import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.card import AbilityAsksThePlayer


class PassiveUpgradeTests(unittest.TestCase):
    """
    The table stacks an upgrade away when nothing on it is ever offered to the
    player. Getting that wrong in one direction hides a card you have to click;
    in the other it leaves a row as crowded as before.
    """

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def IsPassive(self, name: str) -> bool:
        for card_id, paper in CardsDB.papers.items():
            if paper.name == name and paper.type == 'Upgrade':
                abilities = CardsDB.FindAbilities(card_id, paper.pack, paper.set_name)
                return not any(AbilityAsksThePlayer(x) for x in abilities)
        self.fail(f"no upgrade named {name} in this installation")

    def test_upgrades_that_only_change_a_stat_are_passive(self):
        for name in ["Superhuman Strength", "Combat Training", "Vibranium Suit",
                     "Reinforced Suit", "Inspired"]:
            with self.subTest(name):
                self.assertTrue(self.IsPassive(name))

    def test_upgrades_the_player_has_to_use_are_not(self):
        # An Action, a Response and an Interrupt, one of each.
        for name in ["Arc Reactor", "Mission Leader", "Telekinetic Force Field"]:
            with self.subTest(name):
                self.assertFalse(self.IsPassive(name))

    def test_a_forced_response_does_not_make_a_card_active(self):
        # Nothing to answer: it resolves itself, so the card is still one you
        # only read. Without this the flag would be false for most of the pool.
        forced = [
            x
            for card_id, paper in CardsDB.papers.items() if paper.type == 'Upgrade'
            for x in CardsDB.FindAbilities(card_id, paper.pack, paper.set_name)
            if x.flags.is_forced and (x.flags.is_response or x.flags.is_interrupt)
        ]
        self.assertTrue(forced, "expected the pool to contain forced triggers")
        self.assertFalse(any(AbilityAsksThePlayer(x) for x in forced))


if __name__ == '__main__':
    unittest.main()
