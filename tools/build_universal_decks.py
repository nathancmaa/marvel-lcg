"""Build data/universal_decks.json from the Universal Prebuilt Decks sheet.

The geeklist behind data/aspect_decks.json carries a second set of decks: one
per hero, built so that a full collection can hold every one of them at the
same time without moving a card between decks. The aspect decks pair with any
hero; these are the hero's own.

    https://boardgamegeek.com/geeklist/278797/marvel-champions-universal-prebuilt-decks

The list's contents live in a public Google Sheet, one column pair per hero --
card name, card type -- stacked down the rows. This reads that sheet and
resolves the names against data/cards.json, because names are what the sheet
has and card ids are what the game plays with.

It exists rather than the JSON being written by hand for one reason: a deck
list that cannot be rebuilt is a deck list nobody can check. Run it again when
the sheet changes or a pack lands, and the diff says what moved.

    python tools/build_universal_decks.py            # download the sheet
    python tools/build_universal_decks.py --csv x.csv
    python tools/build_universal_decks.py --report   # print, write nothing

A deck is only written when every one of its cards resolves and it is the
right size. A deck missing three copies of a card this installation does not
implement is not a playable deck, and shipping it would put the failure in
front of the player mid-game rather than here.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import os
import re
import sys
import urllib.request
from typing import Any, Dict, List, Sequence, Tuple

SHEET_ID = '1uDnn-7Urtprf3awFV0cSUHseIqJQYCVF7ckineFVBP4'
SHEET_CSV_URL = (
    f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'
)
GEEKLIST_URL = (
    'https://boardgamegeek.com/geeklist/278797/'
    'marvel-champions-universal-prebuilt-decks'
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_JSON = os.path.join(ROOT, 'data', 'cards.json')
STARTER_DECKS = os.path.join(ROOT, 'deck', 'starter')
OUTPUT_JSON = os.path.join(ROOT, 'data', 'universal_decks.json')

# The classes a player deck can draw on. Everything else in cards.json is a
# hero's own signature card or an encounter card, and a name that only matches
# one of those is not the card the sheet means.
PLAYER_CLASSES = frozenset(
    {'Aggression', 'Justice', 'Leadership', 'Protection', "'Pool", 'Basic'}
)

# A hero deck is 15 signature cards; the player deck completes the 40.
PLAYER_DECK_SIZE = 25

# Where the sheet's hero column and this installation's starter deck disagree
# on the name. Kept explicit and small: a silent near-match is how a deck ends
# up filed under the wrong hero, and the run fails on anything not listed here
# rather than guessing.
HERO_ALIASES = {
    # Two heroes share each of these names, so the subtitle is the only thing
    # telling them apart and every one of the four is spelled out.
    'Spider-Man (Peter Parker)': 'spider_man',
    'Spider-Man (Miles Morales)': 'spider_man_miles_morales',
    "Black Panther (T'Challa)": 'black_panther',
    'Black Panther (Shuri)': 'black_panther_shuri',
    'Ant-Man (Scott Lang)': 'ant_man',
    'SP//dr Suit (Peni Parker)': 'sp_dr',
    # The sheet's own typo, kept here rather than corrected upstream.
    'Winter Solider (Bucky Barnes)': 'winter_soldier',
    # This installation disambiguates her from the Defenders-era deck.
    'Jessica Jones': 'jessica_jones',
}


def slug(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')


def split_label(label: str) -> Tuple[str, str]:
    """"Daredevil (Matt Murdock)" -> ("Daredevil", "Matt Murdock")."""
    match = re.match(r'^(.*?)\s*\(([^()]*)\)\s*$', label)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return label.strip(), ''


def load_cards() -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """Player cards indexed by (name, subtitle) and by (name, '')."""
    with io.open(CARDS_JSON, encoding='utf-8') as handle:
        packs = json.load(handle)

    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = collections.defaultdict(list)
    for pack, cards in packs.items():
        if not isinstance(cards, list):
            continue
        for card in cards:
            card_id = str(card.get('card_id', ''))
            if not card_id.isdigit():
                continue
            desc = card.get('desc')
            card_class = desc.get('Class') if isinstance(desc, dict) else None
            if card_class not in PLAYER_CLASSES:
                continue
            # A unique card is starred in the database and not in the sheet.
            name = re.sub(r'^\*\s*', '', str(card.get('name', ''))).strip()
            subtitle = str(card.get('subtitle', '') or '').strip()
            entry = {
                'id': card_id,
                'type': card.get('type'),
                'class': card_class,
                'pack': pack,
                'name': name,
            }
            index[(name.lower(), subtitle.lower())].append(entry)
            index[(name.lower(), '')].append(entry)
    return index


def candidates_for(
    index: Dict[Tuple[str, str], List[Dict[str, Any]]],
    label: str,
    card_type: str,
) -> List[Dict[str, Any]]:
    """Every card that could be what this sheet cell names."""
    name, subtitle = split_label(label)
    candidates = (
        index.get((name.lower(), subtitle.lower()))
        or index.get((name.lower(), ''))
        or []
    )
    typed = [card for card in candidates if not card_type or card['type'] == card_type]
    return typed or candidates


def resolve_card(
    index: Dict[Tuple[str, str], List[Dict[str, Any]]],
    label: str,
    card_type: str,
    prefer: frozenset = frozenset(),
) -> Dict[str, Any] | None:
    """The card the sheet means, or None if this installation has no such card.

    `prefer` is the deck's own aspect. It matters because several names belong
    to more than one card: there is a Justice Spider-Man ally and a Protection
    one, a Justice Spider-Woman and an Aggression one. A deck may only play one
    aspect, so the copy in the deck's aspect is the one the sheet means --
    without this the resolver quietly builds an illegal deck out of real cards,
    which is the worst kind of wrong here because every card in it exists.
    """
    candidates = candidates_for(index, label, card_type)
    if not candidates:
        return None

    if prefer:
        in_aspect = [
            card for card in candidates
            if card['class'] in prefer or card['class'] == 'Basic'
        ]
        candidates = in_aspect or candidates

    # Several cards have been printed twice under one name -- Ever Vigilant,
    # Taunt, Lead from the Front -- with the same cost, class and text. The
    # sheet cares which physical copy a deck uses, because its whole premise is
    # that no two decks share one; nothing here does, so take the earliest
    # printing and take it the same way every run.
    return sorted(candidates, key=lambda card: card['id'])[0]


def deck_aspect(
    index: Dict[Tuple[str, str], List[Dict[str, Any]]],
    cells: Sequence[Tuple[str, str]],
) -> frozenset:
    """Which aspect a deck is in, read from the cards that name only one card.

    Most of a deck is unambiguous, and a Marvel Champions deck plays a single
    aspect -- barring the handful of heroes whose identity says otherwise, who
    come out of this with the two or four they are entitled to.
    """
    classes: collections.Counter = collections.Counter()
    for label, card_type in cells:
        candidates = candidates_for(index, label, card_type)
        if len({card['id'] for card in candidates}) != 1:
            continue
        card_class = candidates[0]['class']
        if card_class != 'Basic':
            classes[card_class] += 1
    return frozenset(classes)


def load_heroes() -> Dict[str, str]:
    """Starter deck id -> hero name, for every hero this installation has."""
    heroes: Dict[str, str] = {}
    for entry in sorted(os.listdir(STARTER_DECKS)):
        if not entry.endswith('.json') or entry.startswith('#'):
            continue
        path = os.path.join(STARTER_DECKS, entry)
        try:
            with io.open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except Exception:
            continue
        heroes[os.path.splitext(entry)[0]] = str(data.get('name', ''))
    return heroes


def match_hero(label: str, heroes: Dict[str, str]) -> str | None:
    """The starter deck id for a sheet column, or None if there is no such hero."""
    if label in HERO_ALIASES:
        hero_id = HERO_ALIASES[label]
        return hero_id if hero_id in heroes else None

    name, _subtitle = split_label(label)
    wanted = slug(name)
    exact = [hero_id for hero_id, hero in heroes.items() if slug(hero) == wanted]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise SystemExit(
            f'"{label}" matches {sorted(exact)}; add it to HERO_ALIASES'
        )
    return None


def read_sheet(csv_path: str | None) -> List[List[str]]:
    if csv_path:
        with io.open(csv_path, encoding='utf-8', newline='') as handle:
            return list(csv.reader(handle))
    with urllib.request.urlopen(SHEET_CSV_URL, timeout=60) as response:
        text = response.read().decode('utf-8')
    return list(csv.reader(io.StringIO(text, newline='')))


def build(rows: Sequence[Sequence[str]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    index = load_cards()
    heroes = load_heroes()
    columns = [(i, h.strip()) for i, h in enumerate(rows[0]) if h.strip()]

    decks: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for column, label in columns:
        hero_id = match_hero(label, heroes)
        if hero_id is None:
            skipped.append(f'{label}: no such hero in this installation')
            continue

        cells: List[Tuple[str, str]] = []
        for row in rows[2:]:
            if column >= len(row):
                continue
            card_label = row[column].strip()
            if not card_label:
                continue
            cells.append((
                card_label,
                row[column + 1].strip() if column + 1 < len(row) else '',
            ))

        # Read the aspect off the unambiguous cards first, then resolve the
        # rest inside it.
        prefer = deck_aspect(index, cells)

        card_ids: List[str] = []
        classes: collections.Counter = collections.Counter()
        missing: collections.Counter = collections.Counter()
        for card_label, card_type in cells:
            card = resolve_card(index, card_label, card_type, prefer)
            if card is None:
                missing[card_label] += 1
                continue
            card_ids.append(card['id'])
            if card['class'] != 'Basic':
                classes[card['class']] += 1

        if missing:
            detail = ', '.join(
                f'{name} x{count}' for name, count in sorted(missing.items())
            )
            skipped.append(f'{label}: not implemented here -- {detail}')
            continue
        if len(card_ids) != PLAYER_DECK_SIZE:
            skipped.append(
                f'{label}: the sheet lists {len(card_ids)} cards, '
                f'not {PLAYER_DECK_SIZE}'
            )
            continue

        # The aspect a deck is played as, which is not the same as every class
        # in it: a dozen heroes are allowed off-aspect cards by their own
        # identity -- Cable takes player side schemes from anywhere, Cyclops
        # any X-MEN ally, Gamora six attack or thwart events -- and those
        # cards are in the deck legally without being what it is. The two
        # heroes who really do play more than one aspect, Spider-Woman and
        # Adam Warlock, hold an equal number of each and so come out named
        # for all of them.
        ranked = classes.most_common()
        top = ranked[0][1] if ranked else 0
        aspects = sorted(name for name, count in ranked if count == top)
        decks.append({
            'id': hero_id,
            'hero': hero_id,
            'hero_name': heroes[hero_id],
            'name': f'Universal {heroes[hero_id]}',
            'aspect': ' / '.join(aspects),
            'player_deck': card_ids,
        })

    decks.sort(key=lambda deck: deck['hero_name'].lower())
    return decks, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', help='a downloaded copy of the sheet')
    parser.add_argument('--out', default=OUTPUT_JSON)
    parser.add_argument(
        '--report', action='store_true', help='print the summary, write nothing'
    )
    args = parser.parse_args()

    rows = read_sheet(args.csv)
    decks, skipped = build(rows)

    print(f'{len(decks)} decks built, {len(skipped)} columns skipped')
    for line in skipped:
        print(f'  - {line}')

    by_aspect = collections.Counter(deck['aspect'] for deck in decks)
    print('by aspect: ' + ', '.join(
        f'{aspect} {count}' for aspect, count in sorted(by_aspect.items())
    ))

    if args.report:
        return 0

    payload = {
        'source': 'Universal Prebuilt Decks, a BoardGameGeek geeklist',
        'source_url': GEEKLIST_URL,
        'sheet_url': SHEET_CSV_URL,
        'generated_by': 'tools/build_universal_decks.py',
        'decks': decks,
    }
    with io.open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(f'wrote {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
