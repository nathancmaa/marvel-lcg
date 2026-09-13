"""A deck's aspects are the ones it plays, not every one it carries a card of."""
import json
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.version import Ver
from game.statistics.deck_aspects import DeckAspects, WithDeckAspects


def starter(name: str) -> dict:
    with open(f'deck/starter/{name}.json', encoding='utf-8') as handle:
        return json.load(handle)


class DeckAspectsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def test_a_one_aspect_deck_names_one(self):
        self.assertEqual(DeckAspects(starter('spider_man')['player_deck']), ['Justice'])

    def test_cables_own_side_schemes_do_not_make_his_deck_three_aspects(self):
        # One Aggression card and one Protection card, both his signature
        # side schemes; the deck plays Leadership.
        self.assertEqual(DeckAspects(starter('cable')['player_deck']), ['Leadership'])

    def test_spider_woman_plays_two_and_adam_warlock_four(self):
        self.assertEqual(
            DeckAspects(starter('spider_woman')['player_deck']),
            ['Aggression', 'Justice'])
        self.assertEqual(
            DeckAspects(starter('adam_warlock')['player_deck']),
            ['Aggression', 'Justice', 'Leadership', 'Protection'])

    def test_most_played_aspect_comes_first(self):
        aspects = DeckAspects(starter('gamora')['player_deck'])
        self.assertEqual(aspects[0], 'Aggression')
        self.assertEqual(sorted(aspects[1:]), ['Justice', 'Protection'])

    def test_a_deck_of_no_aspect_cards_and_unknown_ids_is_harmless(self):
        self.assertEqual(DeckAspects([]), [])
        self.assertEqual(DeckAspects(['99999', '', None]), [])
        deck = WithDeckAspects({'name': 'x', 'player_deck': starter('spider_man')['player_deck']})
        self.assertEqual(deck['aspects'], ['Justice'])


if __name__ == '__main__':
    unittest.main()
