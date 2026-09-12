"""Heroes that share a name are told apart by their alter ego, and only those."""
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.version import Ver
from game.statistics import hero_labels
from game.statistics.hero_labels import HeroLabel


class HeroLabelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        hero_labels.Reset()

    def test_the_two_black_panthers_and_two_spider_men_read_apart(self):
        self.assertEqual(HeroLabel('01040a', 'Black Panther'), "Black Panther (T'Challa)")
        self.assertEqual(HeroLabel('51001a', 'Black Panther'), 'Black Panther (Shuri)')
        self.assertEqual(HeroLabel('01001a', 'Spider-Man'), 'Spider-Man (Peter Parker)')
        self.assertEqual(HeroLabel('27030a', 'Spider-Man'), 'Spider-Man (Miles Morales)')

    def test_a_hero_with_one_identity_keeps_a_plain_name(self):
        # Ant-Man's second identity card is still Scott Lang; Ironheart's
        # three are all Riri Williams. Nothing to tell apart.
        self.assertEqual(HeroLabel('12001a', 'Ant-Man'), 'Ant-Man')
        self.assertEqual(HeroLabel('29001a', 'Ironheart'), 'Ironheart')
        self.assertEqual(HeroLabel('01094', 'Rhino'), 'Rhino')

    def test_a_name_already_labelled_is_left_alone(self):
        self.assertEqual(HeroLabel('51001a', 'Black Panther (Shuri)'), 'Black Panther (Shuri)')

    def test_an_unknown_code_or_empty_name_is_harmless(self):
        self.assertEqual(HeroLabel('99999a', 'Black Panther'), 'Black Panther')
        self.assertEqual(HeroLabel(None, 'Black Panther'), 'Black Panther')
        self.assertEqual(HeroLabel('51001a', ''), '')


if __name__ == '__main__':
    unittest.main()
