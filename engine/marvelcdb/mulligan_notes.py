"""Reading a deck author's mulligan advice out of a MarvelCDB description.

Deck descriptions on MarvelCDB are free markdown, and authors write about the
opening hand wherever it suits them. Looking for a "Mulligan" section finds
almost nothing: across a 25-deck sample, twelve mentioned mulligans and only
*one* put a heading on it. Extracting sections would have looked like it worked
while missing eleven of twelve, which is the worst kind of failure -- silent.

What is reliable is the card links. Descriptions cite cards as
`[Meditation](/card/26036)`, and ten of those twelve linked at least one card
within a sentence or two of the advice. Those links are the extraction: the
cards an author names while talking about the opening hand are the cards they
want you to keep.

Nothing here interprets the advice. It collects which cards were named and the
sentence that named them, so the player reads the author's own words and
decides.
"""

import re
from typing import Any, Dict, List, Tuple

# What counts as talking about the opening hand.
MULLIGAN_PHRASE = re.compile(r'mulligan|opening hand|starting hand', re.I)

# MarvelCDB writes card citations as [Display Name](/card/01234), and -- when
# an author pastes the address bar rather than using the editor's card button --
# as the same link spelled absolutely. Missing the second form cost two decks
# out of ninety-six, which is small until you are one of them.
CARD_LINK = re.compile(
    r'\[([^\]]{1,60})\]\((?:https?://(?:www\.)?marvelcdb\.com)?/card/(\d+[a-z]?)\)')

# Some authors just write the name. Matching prose against arbitrary card names
# would be reckless, so this only ever matches names belonging to *this deck*,
# on whole words, longest first -- without which "Vibranium" claims the mention
# of "Vibranium Suit" sitting next to it.
MIN_NAME = 5

# How far either side of a mention to look for cited cards. A sentence or two:
# wide enough for "mulligan hard for X and Y", narrow enough not to drag in the
# unrelated paragraph after it.
LOOK_BEHIND = 200
LOOK_AHEAD = 300

# Kept small on purpose. The deck this is stored on travels to the table in a
# URL query string, so a few hundred bytes is the budget, not a few thousand.
MAX_CARDS = 8
MAX_NOTE = 240


def _clean(markdown: str) -> str:
    """Card links reduced to their names, and the markup dropped."""
    text = CARD_LINK.sub(lambda match: match.group(1), markdown)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[*_`#]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _sentence_around(text: str, index: int) -> str:
    """The sentence containing `index`, as the author wrote it."""
    start = max(
        text.rfind('. ', 0, index),
        text.rfind('\n', 0, index),
        text.rfind('! ', 0, index),
    )
    start = 0 if start < 0 else start + 1
    ends = [pos for pos in (
        text.find('. ', index), text.find('\n', index), text.find('! ', index),
    ) if pos != -1]
    end = min(ends) + 1 if ends else len(text)
    return text[start:end].strip()


def _named_in(window: str, deck_cards: Dict[str, str]) -> List[str]:
    """Card ids whose names this passage spells out, longest name first."""
    found: List[str] = []
    haystack = window.lower()
    taken: List[Tuple[int, int]] = []
    for name in sorted(deck_cards, key=len, reverse=True):
        if len(name) < MIN_NAME:
            continue
        for match in re.finditer(r'\b' + re.escape(name) + r'\b', haystack):
            span = match.span()
            # A longer name already claimed this text; the shorter one is part
            # of it rather than a second card.
            if any(start <= span[0] and span[1] <= end for start, end in taken):
                continue
            taken.append(span)
            card_id = deck_cards[name]
            if card_id not in found:
                found.append(card_id)
            break
    return found


def ExtractMulliganAdvice(
    description: str,
    deck_cards: Dict[str, str]|None = None,
) -> Tuple[List[str], str]:
    """The cards an author names about the opening hand, and why.

    Returns ``(card_ids, note)``. Both are empty when the description says
    nothing usable about the opening hand, which measured across a whole
    96-deck collection is about three decks in four -- an ordinary answer and
    not a failure. (An early 25-deck sample suggested two in five; the full
    collection is the number to trust.)
    """
    text = str(description or '')
    if not text.strip():
        return [], ''

    by_name = {name.lower(): card_id for name, card_id in (deck_cards or {}).items()}
    card_ids: List[str] = []
    notes: List[str] = []
    for match in MULLIGAN_PHRASE.finditer(text):
        window = text[max(0, match.start() - LOOK_BEHIND): match.start() + LOOK_AHEAD]
        linked = [card_id for _, card_id in CARD_LINK.findall(window)]
        # Links are the author being explicit and are always preferred; names
        # are only consulted where they linked nothing at all, so a deck that
        # cites properly can never have prose dragged in beside it.
        for card_id in linked or _named_in(window, by_name):
            if card_id not in card_ids:
                card_ids.append(card_id)
        sentence = _clean(_sentence_around(text, match.start()))
        if sentence and sentence not in notes:
            notes.append(sentence)

    if not card_ids:
        # A mention with nothing cited cannot be acted on, and a note with no
        # cards to point at is advice without a subject.
        return [], ''

    note = ' '.join(notes)
    if len(note) > MAX_NOTE:
        note = note[:MAX_NOTE - 1].rstrip() + '…'
    return card_ids[:MAX_CARDS], note


def AttachMulliganAdvice(
    metadata: Dict[str, Any],
    description: str,
    deck_cards: Dict[str, str]|None = None,
) -> None:
    """Record the advice on a converted deck, if the description carries any."""
    card_ids, note = ExtractMulliganAdvice(description, deck_cards)
    if not card_ids:
        return
    metadata['mulligan_cards'] = ','.join(card_ids)
    metadata['mulligan_note'] = note
