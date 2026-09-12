import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.card import AbilityIsAnswerable


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

    def test_a_response_that_waits_on_its_event_still_counts(self):
        # "After you defeat a minion" and "After you change form" are built as
        # a forced wrapper that registers the response once the event comes.
        # The card still prints a Response, and the game still stops to ask.
        for name, card_type in [("Hall of Heroes", "Support"),
                                ("Ready to Rumble", "Upgrade")]:
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
