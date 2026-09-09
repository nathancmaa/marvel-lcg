"""The generated universal decks are decks this installation can actually play.

data/universal_decks.json is built by tools/build_universal_decks.py from a
public sheet, so nobody reads it line by line. These assertions are what a
reader would check: the heroes exist, the cards exist, and each deck is the
size that makes a legal 40 with a hero's 15 signature cards.

The generator already refuses to write a deck that fails any of this. The point
of repeating it here is that the file is committed and the generator is not run
again for months -- a pack that renames or removes a card breaks the file
quietly, and this is what says so.
"""

import io
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECKS_JSON = ROOT / 'data' / 'universal_decks.json'
CARDS_JSON = ROOT / 'data' / 'cards.json'
STARTER_DECKS = ROOT / 'deck' / 'starter'

PLAYER_DECK_SIZE = 25


def load_json(path):
    with io.open(path, encoding='utf-8') as handle:
        return json.load(handle)


class UniversalDeckTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_json(DECKS_JSON)
        cls.decks = cls.file['decks']

        cards = load_json(CARDS_JSON)
        cls.card_ids = set()
        for pack, entries in cards.items():
            if not isinstance(entries, list):
                continue
            for card in entries:
                cls.card_ids.add(str(card.get('card_id', '')))

        cls.heroes = {
            path.stem for path in STARTER_DECKS.glob('*.json')
            if not path.name.startswith('#')
        }

    def test_the_file_says_where_it_came_from(self):
        """A generated file that does not name its source cannot be checked."""
        self.assertIn('boardgamegeek.com', self.file['source_url'])
        self.assertEqual(
            self.file['generated_by'], 'tools/build_universal_decks.py')
        self.assertTrue(self.decks, 'no decks were generated')

    def test_every_deck_belongs_to_a_hero_this_installation_has(self):
        for deck in self.decks:
            with self.subTest(deck=deck['id']):
                self.assertIn(deck['hero'], self.heroes)
                self.assertEqual(deck['id'], deck['hero'])

    def test_no_hero_has_two_decks(self):
        heroes = [deck['hero'] for deck in self.decks]
        self.assertEqual(len(heroes), len(set(heroes)))

    def test_every_card_is_one_this_installation_implements(self):
        """The failure this exists for: a card that stopped being in cards.json.

        A deck naming a card the engine does not have does not fail at start-up.
        It fails when the card is drawn, which is mid-game and much later.
        """
        for deck in self.decks:
            for card_id in deck['player_deck']:
                with self.subTest(deck=deck['id'], card=card_id):
                    self.assertIn(card_id, self.card_ids)

    def test_every_deck_completes_a_forty_card_deck(self):
        """25 aspect and basic cards, to go with a hero's 15 signature cards."""
        for deck in self.decks:
            with self.subTest(deck=deck['id']):
                self.assertEqual(len(deck['player_deck']), PLAYER_DECK_SIZE)

    def test_no_card_appears_more_than_three_times(self):
        """The deckbuilding limit, and a cheap check on the name matching.

        Four copies of one card means two different cards resolved to the same
        id, which is exactly the mistake a name-matched deck list invites.
        """
        for deck in self.decks:
            counts = {}
            for card_id in deck['player_deck']:
                counts[card_id] = counts.get(card_id, 0) + 1
            for card_id, count in counts.items():
                with self.subTest(deck=deck['id'], card=card_id):
                    self.assertLessEqual(count, 3)

    def test_every_deck_names_an_aspect(self):
        for deck in self.decks:
            with self.subTest(deck=deck['id']):
                self.assertTrue(deck['aspect'].strip())
                self.assertTrue(deck['name'].strip())
                self.assertTrue(deck['hero_name'].strip())


if __name__ == '__main__':
    unittest.main()
