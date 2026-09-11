import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.card import (
    AbilityAsksThePlayer,
    AbilityIsAnswerable,
    CardPrintsAResourceAbility,
)


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
        """The same two tests the card descriptor makes, in the same order.

        The printed line has to be one of them. Asking the abilities alone
        cannot see a resource: at runtime every card carries a CheckResource
        effect, because any card can be discarded for the icons printed on it,
        so that question comes back yes for everything.
        """
        for card_id, paper in CardsDB.papers.items():
            if paper.name == name and paper.type == 'Upgrade':
                abilities = CardsDB.FindAbilities(card_id, paper.pack, paper.set_name)
                return not any(AbilityAsksThePlayer(x) for x in abilities)                     and not CardPrintsAResourceAbility(paper.text)
        self.fail(f"no upgrade named {name} in this installation")

    def test_upgrades_that_only_change_a_stat_are_passive(self):
        for name in ["Superhuman Strength", "Combat Training", "Vibranium Suit",
                     "Reinforced Suit", "Inspired"]:
            with self.subTest(name):
                self.assertTrue(self.IsPassive(name))

    def test_a_card_you_spend_is_not_passive(self):
        # Spending a card to pay for another is a click on that card, so none
        # of these is text you only read and none belongs stacked out of reach.
        #
        # Nearly all of them say so with a CheckResource ability rather than a
        # Resource one, and CheckResource is declared forced -- the game tests
        # it rather than offering it. Reading only the unforced abilities is
        # what collapsed Web-Shooter and forty-eight others; Fury's Watch and
        # Jet Belt are the two that carry a Resource ability outright, which is
        # why they alone looked like the whole problem.
        # The last four were in one game's collapsed stacks when this was
        # reported, which is how the CheckResource case came to light.
        for name in ["Fury's Watch", "Jet Belt", "Web-Shooter", "Expert Marksman",
                     "God of Thunder", "Clarity of Purpose", "Grim Resolve",
                     "X-Gene", "Prehensile Tail"]:
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
