"""A "spend X or suffer Y" choice must be answered with one of its halves.

Klaw's Sonic Boom: "Spend a [energy][mental][physical] resource, or exhaust
each character you control." The ask was offered with Cancel, and Cancel --
or backing out of the payment -- skipped both halves. It is played here in a
real headless game: the ask is forced, a payment not made puts it again, and
each half does what it says.
"""

import contextlib
import io
import unittest

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager

SONIC_BOOM = "01123"
FIXTURE = Fixture(
    "klaw",
    ("spider_man",),
    424245,
    (
        'Puzzle.ClearHand()',
        # One card of each resource the payment needs.
        'Puzzle.CreateHandCards("01002", "01003", "01004")',
        f'Puzzle.Reveal("{SONIC_BOOM}")',
    ),
)


def is_sonic_boom(prompt) -> bool:
    return prompt.event_name == 'WhenPlayerChooseAbility' and 'Sonic Boom' in prompt.prompt_text


def option_named(prompt, prefix: str) -> dict:
    for option in prompt.options:
        if option['name'].startswith(prefix):
            return option
    raise AssertionError(f"no {prefix} option in {[o['name'] for o in prompt.options]}")


def payment_for(option: dict) -> list:
    """Resource ids paying the option's cost, one per resource, from the hand."""
    payment = next(iter(option['target_payment'].values()))
    offered = [(str(effect_id), res) for entry in payment['payment'] for effect_id, res in entry.items()]
    chosen = []
    for res in payment['cost']:
        # The last offers are the hand cards placed by the fixture.
        for effect_id, offered_res in reversed(offered):
            if offered_res == res and effect_id not in chosen:
                chosen.append(effect_id)
                break
    assert len(chosen) == len(payment['cost']), f"{payment=}"
    return chosen


def play(answers):
    """Answer the Sonic Boom asks in order, then stop at the next other ask."""
    answers = list(answers)
    asks: list = []

    def choose(prompt):
        if not is_sonic_boom(prompt):
            return None
        asks.append(prompt)
        if not answers:
            return None
        return answers.pop(0)(prompt)

    devices = HeadlessDeviceManager(choice_provider=choose)
    with contextlib.redirect_stdout(io.StringIO()):
        game = run_fixture(FIXTURE, devices)
    player = game.world.GetFirstPlayer()
    return game, player, asks


class SpendOrSufferChoiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_sonic_boom_offers_no_cancel(self):
        _, _, asks = play([])
        self.assertEqual(len(asks), 1)
        self.assertFalse(asks[0].show_cancel)

    def test_cancel_and_an_unmade_payment_ask_again(self):
        def cancel(prompt):
            return CommandDescriptor()

        def spend_nothing(prompt):
            return CommandDescriptor(str(option_named(prompt, 'Spend')['id']), [], [])

        _, player, asks = play([cancel, spend_nothing])

        # Neither answer took a half: the ask came back each time, and
        # nothing was paid or exhausted.
        self.assertEqual(len(asks), 3)
        self.assertEqual(len(player.hand_cards.Get()), 3)
        self.assertFalse(player.GetIdentity().IsExhaust())

    def test_spending_the_resources_pays_instead_of_exhausting(self):
        def spend(prompt):
            option = option_named(prompt, 'Spend')
            return CommandDescriptor(str(option['id']), [], payment_for(option))

        _, player, asks = play([spend])

        self.assertEqual(len(asks), 1)
        self.assertEqual(player.hand_cards.Get(), [])
        self.assertFalse(player.GetIdentity().IsExhaust())

    def test_exhausting_takes_the_other_half(self):
        def exhaust(prompt):
            option = option_named(prompt, 'Exhaust')
            targets = [str(t) for t in option['all_legal_targets']]
            return CommandDescriptor(str(option['id']), targets, [])

        _, player, asks = play([exhaust])

        self.assertEqual(len(asks), 1)
        self.assertTrue(player.GetIdentity().IsExhaust())
        self.assertEqual(len(player.hand_cards.Get()), 3)


class MaySpendOfferTests(unittest.TestCase):
    """An ask made only of a payment is an offer, and Cancel declines it."""

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_a_may_spend_offer_keeps_its_cancel(self):
        # Bandolier of Stakes: "you may spend 1 resource" to attach it.
        fixture = Fixture(
            "klaw",
            ("spider_man",),
            424246,
            ('Puzzle.ClearHand()', 'Puzzle.CreateHandCards("01002")', 'Puzzle.Reveal("39048")'),
        )
        asks: list = []

        def decline(prompt):
            if prompt.event_name != 'WhenPlayerChooseAbility' or asks:
                return None
            asks.append(prompt)
            return CommandDescriptor()

        devices = HeadlessDeviceManager(choice_provider=decline)
        with contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, devices)
        player = game.world.GetFirstPlayer()

        self.assertEqual(len(asks), 1)
        self.assertTrue(asks[0].show_cancel)
        # Declined: nothing paid, and the attachment was not attached.
        self.assertEqual(len(player.hand_cards.Get()), 1)
        self.assertNotIn("39048", [f.paper.card_id for f in player.GetIdentity().GetInventoryDeck().Get()])
        self.assertIn("39048", [f.paper.card_id for f in game.world.scenario.encounter_discard_pile.Get()])
        self.assertNotIn("WhenPlayerChooseAbility", devices.stopped_prompt.event_name)


if __name__ == "__main__":
    unittest.main()
