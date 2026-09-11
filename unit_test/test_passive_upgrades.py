import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.card import AbilityAsksThePlayer, AbilityIsAnswerable


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

    def test_a_card_you_spend_is_not_passive(self):
        # Their only ability is a Resource -- Fury's Watch a plain one, Jet
        # Belt a Hero Resource. Spending a card to pay for another is a click
        # on that card, so neither is text you only read, and neither belongs
        # stacked out of reach behind its neighbours.
        for name in ["Fury's Watch", "Jet Belt"]:
            with self.subTest(name):
                self.assertFalse(self.IsPassive(name))

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


class AnswerableAbilityTests(unittest.TestCase):
    """
    A card offers the standing-answer tick when it has something the game will
    stop and ask about. Offering it on everything is what made the mark look
    like it meant something on cards it could never apply to.
    """

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def Answerable(self, name: str, card_type: str) -> bool:
        for card_id, paper in CardsDB.papers.items():
            if paper.name == name and paper.type == card_type:
                abilities = CardsDB.FindAbilities(card_id, paper.pack, paper.set_name)
                return any(AbilityIsAnswerable(x) for x in abilities)
        self.fail(f"no {card_type} named {name} in this installation")

    def test_a_response_or_interrupt_is_answerable(self):
        for name, card_type in [("Honey Badger", "Ally"), ("Graymalkin", "Support"),
                                ("Mission Leader", "Upgrade"),
                                ("Telekinetic Force Field", "Upgrade")]:
            with self.subTest(name):
                self.assertTrue(self.Answerable(name, card_type))

    def test_an_action_alone_is_not(self):
        # Plasma Rifle is a Hero Action. Marking it used to let the table post
        # for it, which is how an ally with a tick attacked on a click.
        self.assertFalse(self.Answerable("Plasma Rifle", "Upgrade"))

    def test_a_forced_trigger_is_not(self):
        # The attachment fires itself; there is no question to stand an answer
        # against, so it never wears a tick.
        self.assertFalse(self.Answerable("Telekinetic Force Field", "Attachment"))


if __name__ == '__main__':
    unittest.main()
