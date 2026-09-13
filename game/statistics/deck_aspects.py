"""Which aspects a deck plays, read off its cards.

A deck does not say its aspect; its cards do. Most decks are one aspect, but
Spider-Woman's is two, Adam Warlock's is all four, and the pickers should say
so. Cable's is one: the lone Aggression and Protection cards in it are his
own side schemes, and a single card of an aspect is not the deck playing it.
Three or more of one aspect is -- "more than a couple", which keeps Cable to
Leadership and gives Adam Warlock his four.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List

# The classes that are aspects, as cards.json spells them. 'Pool is
# Deadpool's own; his decks carry no standard aspect card at all.
ASPECT_CLASSES = ('Aggression', 'Justice', 'Leadership', 'Protection', "'Pool")

# How many cards of an aspect make the deck play it.
CARDS_TO_COUNT = 3

# A handful of cards carry two classes joined by a semicolon, e.g.
# "Hero;Aggression", so the field is split rather than compared whole.
CLASS_SEPARATOR = ';'


def DeckAspects(card_ids: Iterable[str]) -> List[str]:
    """The aspects a deck plays, most cards first; empty when it plays none."""
    try:
        from cards.database import CardsDB
        papers = CardsDB.papers
    except Exception:
        return []
    tally: Counter[str] = Counter()
    for card_id in card_ids:
        paper = papers.get(str(card_id).strip())
        desc = getattr(paper, 'desc', None) if paper else None
        card_class = desc.get('Class', '') if isinstance(desc, dict) else ''
        for part in str(card_class or '').split(CLASS_SEPARATOR):
            if part in ASPECT_CLASSES:
                tally[part] += 1
    return [
        aspect for aspect, count in
        # Most cards first; the alphabet settles a tie so the label is stable.
        sorted(tally.items(), key=lambda item: (-item[1], item[0]))
        if count >= CARDS_TO_COUNT
    ]


def WithDeckAspects(deck: dict) -> dict:
    """Write the deck's aspects into it as `aspects`, for the pickers."""
    if isinstance(deck, dict):
        deck['aspects'] = DeckAspects(deck.get('player_deck') or [])
    return deck
