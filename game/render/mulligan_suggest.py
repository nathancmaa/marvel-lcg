"""Guessing which cards are worth keeping, for decks whose author said nothing.

This is the fallback behind `mulligan_notes`, which quotes what a deck's author
actually wrote. Roughly a quarter of synced decks carry such a note; the rest
get this, and precons and aspect decks get it always.

The weights are not invented. They were measured against the 23 decks in a
96-deck collection whose descriptions named cards around the mulligan -- 92
named cards that are actually drawable, scored against every other card in the
same deck, so a card type cannot look predictive merely by being common.

What that measurement found, in order of how much it surprised me:

  * Cost does not predict. Across the curve the lift is 1.09 to 1.25 -- flat.
    The folk rule "keep the cheap cards you can play on turn one" has no
    support here, and the cards authors name cost *more* than average (1.80
    against 1.45). So cost is absent from the scoring below, deliberately.
  * Plain resource cards score 0.17. Authors essentially never tell you to
    keep one, which is the strongest single signal in the data.
  * Allies score 0.42, which is the same surprise from the other side: a cheap
    ally is a fine turn-one play and almost never what you dig for.
  * What authors do dig for is the engine -- an Upgrade or a Support, often one
    they run three of, often part of the hero's own kit.
  * Deck theme adds nothing (1.01). Unlike card substitution, where trait
    synergy carries real weight, the mulligan does not care what the deck is
    built around.

Honest about how good this is: leave-one-deck-out, the top five catches 27% of
the author's picks where random guessing catches 17%. That is a real signal and
a modest one. It is also a floor rather than an estimate, because an author
naming four cards out of forty does not mark the other thirty-six as bad keeps
-- there are no true negatives in the data, so the 27% understates the scorer by
an amount nothing here can measure. This is why the panel labels these picks as
its own and never as the author's: the two are not the same kind of claim.
"""

from collections import Counter
from typing import Any, Dict, List, Sequence, Tuple

# Rounded from the measured per-feature lifts into tiers, because three
# significant figures would claim a precision 92 data points do not support.
UPGRADE_OR_SUPPORT = 0.6
# The least stable of these: it ranged 0.92 to 1.99 across twenty half-splits
# of the first 23 decks, and settled to 1.41 once the ground truth grew to 31.
# Recall is flat between 0.4 and 0.6, so this follows the measurement rather
# than the marginally better number.
SIGNATURE = 0.4
THREE_COPIES = 0.7
TEXT_HINT = 0.6
EVENT = 0.2
ALLY = -0.6
RESOURCE = -0.8

# Words that mark a card as doing something for the rest of the deck rather
# than for itself. Measured at ~1.6 each, and deliberately crude: matching
# rules text this loosely is why they are worth only as much as a card type.
TEXT_HINTS = ('draw', 'ready', 'resource')

# A hand's worth. Fewer looks more confident than the evidence allows; more
# stops being a recommendation and becomes a list.
SUGGESTION_COUNT = 5

# Decks are fixed for a game, so this is computed once and kept. Bounded
# because a long-running server sees many.
#
# Keyed on the two lists separately, not on the cards combined: whether a card
# is part of the hero's own kit changes its score, so two decks holding the same
# forty cards split differently are different questions with different answers.
_CACHE: Dict[Tuple[Tuple[str, ...], Tuple[str, ...]], List[str]] = {}
_CACHE_LIMIT = 64

# A deck is forty cards and change. This is not a deck size limit -- it is a
# ceiling on what an HTTP body can make the server look up and then remember.
MAX_DECK_CARDS = 500


def _score(paper: Any, copies: int, is_signature: bool) -> float:
    """How much this card looks like something a deck author would dig for."""
    card_type = str(getattr(paper, 'type', ''))
    score = 0.0

    if card_type in ('Upgrade', 'Support'):
        score += UPGRADE_OR_SUPPORT
    elif card_type == 'Event':
        score += EVENT
    elif card_type == 'Ally':
        score += ALLY
    elif card_type == 'Resource':
        score += RESOURCE

    if is_signature:
        score += SIGNATURE
    if copies >= 3:
        score += THREE_COPIES

    # Counted once however many of the words appear. It was measured as a
    # single yes/no feature, and paying per word let a card that happens to say
    # all three outweigh being an Upgrade -- a weight nothing measured.
    text = str(getattr(paper, 'text', '') or '').lower()
    if any(hint in text for hint in TEXT_HINTS):
        score += TEXT_HINT
    return score


def MulliganAdviceFor(
    metadata: Dict[str, Any]|None,
    player_deck: Sequence[str],
    hero_deck: Sequence[str],
) -> Tuple[List[str], str, str]:
    """The advice to show for a deck: the author's if they gave any, else ours.

    Returns ``(card_ids, note, source)`` where source is 'author', 'deck', or
    '' when there is nothing to say. This is the whole policy, in one place,
    because the table and the deck viewer must never disagree about which kind
    of claim they are making.
    """
    meta = metadata or {}
    written = str(meta.get('mulligan_cards', '') or '')
    authored = [card_id for card_id in written.split(',') if card_id]
    if authored:
        return authored, str(meta.get('mulligan_note', '') or ''), 'author'

    ranked = SuggestMulliganCards(player_deck, hero_deck)
    return (ranked, '', 'deck') if ranked else ([], '', '')


def SuggestMulliganCards(
    player_deck: Sequence[str],
    hero_deck: Sequence[str],
) -> List[str]:
    """The cards in this deck most worth keeping, best first.

    Returns an empty list when the card database has not loaded, rather than
    ranking a deck it cannot read -- the panel showing nothing is the correct
    answer to not knowing.
    """
    from cards.database import CardsDB

    if not CardsDB.papers:
        return []

    player_cards = list(player_deck)[:MAX_DECK_CARDS]
    hero_cards = list(hero_deck)[:MAX_DECK_CARDS]
    all_cards = player_cards + hero_cards
    if not all_cards:
        return []

    key = (tuple(sorted(player_cards)), tuple(sorted(hero_cards)))
    cached = _CACHE.get(key)
    if cached is not None:
        return list(cached)

    signature = set(hero_cards)
    counts = Counter(all_cards)
    scored: List[Tuple[float, str, str]] = []
    for card_id, copies in counts.items():
        paper = CardsDB.TryFindCardPaper(card_id)
        if paper is None:
            continue
        score = _score(paper, copies, card_id in signature)
        if score <= 0:
            # A card the measurement actively argues against keeping has no
            # business in a list of what to keep, however short the list is.
            continue
        scored.append((score, str(getattr(paper, 'name', '')), card_id))

    # Name breaks ties so the same deck always suggests the same cards, rather
    # than reordering between renders on equal scores.
    scored.sort(key=lambda row: (-row[0], row[1]))
    suggestions = [card_id for _, _, card_id in scored[:SUGGESTION_COUNT]]

    if len(_CACHE) >= _CACHE_LIMIT:
        _CACHE.clear()
    _CACHE[key] = suggestions
    return list(suggestions)
