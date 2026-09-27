"""Hero obligations resolve their penalty when the player has nothing to lose.

Real games: each obligation is revealed with puzzle commands, and the
choices a player would make at the table are scripted by option name.
"""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


def option_named(prompt, fragment):
    for option in prompt.options:
        if fragment in str(option.get("name", "")):
            return option
    return None


def option_names(prompt):
    return [str(option.get("name", "")) for option in prompt.options]


def pick(option, targets=None, resources=()):
    if targets is None:
        minimum = int(option.get("target_num_range", [0, 0])[0])
        targets = [
            str(target.get("id", target) if isinstance(target, dict) else target)
            for target in option.get("all_legal_targets", [])[:minimum]
        ]
    return CommandDescriptor(
        HeadlessDeviceManager._DescriptorId(option),
        list(targets),
        list(resources),
    )


def payment_effect_ids(option):
    effects = []
    for payment in option.get("target_payment", {}).values():
        for entry in payment.get("payment", []):
            effects.extend(str(effect_id) for effect_id in entry)
    return effects


class Table:
    """Play a fixture; ``answer(prompt)`` returns a command, or None for default."""

    def __init__(self, fixture, answer):
        self.answer = answer
        self.turn_prompt = None
        self.prompts = []
        self.devices = HeadlessDeviceManager(choice_provider=self._provide)
        from game.world.world_render import WorldRender
        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            self.game = run_fixture(fixture, self.devices)
        self.errors = error.call_count
        self.world = self.game.world
        self.player = self.world.GetFirstPlayer()

    def _provide(self, prompt):
        self.prompts.append(prompt)
        if prompt.event_name.startswith("WhenPlayerInTurn"):
            self.turn_prompt = prompt
            return None
        command = self.answer(prompt)
        if command is None:
            command = HeadlessDeviceManager._DefaultChoice(prompt)
        return command


def decline_flip(prompt):
    cancel = option_named(prompt, "Cancel")
    if cancel is not None and option_named(prompt, "Flip_to_alter-ego"):
        return pick(cancel)
    return None


class HeroObligationChoiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_care_for_cassie_with_an_empty_hand_still_locks_the_form(self):
        table = Table(
            Fixture("rhino", ("ant_man",), 5, (
                'Puzzle.ClearHand()',
                'Puzzle.ChangeFormFor(0,"Identity")',
                'Puzzle.Reveal("12025")',
            )),
            decline_flip,
        )

        self.assertEqual(table.errors, 0)
        self.assertTrue(table.player.IsHero())
        self.assertEqual(table.player.obligations_area.Get(), [])
        encounter_discard = table.world.GetScenario().encounter_deck.bind_discard_pile
        self.assertIn("12025", [face.paper.card_id for face in encounter_discard.Get()])
        self.assertFalse(
            [name for name in option_names(table.turn_prompt) if "Scott_Lang" in name],
            "Care for Cassie's penalty should stop Ant-Man changing form",
        )

    def test_red_dreams_without_mental_cards_still_deals_damage(self):
        table = Table(
            Fixture("rhino", ("wasp",), 5, (
                'Puzzle.ClearHand()',
                'Puzzle.ChangeFormFor(0,"Identity")',
                'Puzzle.Reveal("13026")',
            )),
            decline_flip,
        )

        identity = table.player.GetIdentity()
        self.assertEqual(table.errors, 0)
        self.assertEqual(identity.max_health - identity.health, 1)
        self.assertEqual(table.player.obligations_area.Get(), [])

    def innocent_bystanders(self, choose):
        seen = {}

        def answer(prompt):
            spend = option_named(prompt, "Spend_1_resource")
            if spend is not None:
                seen["prompt"] = prompt
                return choose(prompt)
            return None

        table = Table(
            Fixture("rhino", ("spider_man",), 5, (
                'Puzzle.ClearHand()',
                'Puzzle.CreateHandCards("01002")',
                'Puzzle.ChangeFormFor(0,"Identity")',
                'Puzzle.Reveal("50134")',
                'Puzzle.DoAttack("Rhino")',
            )),
            answer,
        )
        self.assertEqual(table.errors, 0)
        return table, seen["prompt"]

    def test_innocent_bystanders_cannot_be_cancelled(self):
        table, prompt = self.innocent_bystanders(
            lambda prompt: pick(option_named(prompt, "threat_on_the_main_scheme")))

        self.assertFalse(prompt.show_cancel)
        self.assertEqual(len(prompt.options), 2)
        main_scheme = table.world.area_schemes_main.Get()[0]
        self.assertEqual(main_scheme.threat, 1)
        bystanders = table.player.obligations_area.Get()[0]
        self.assertEqual(bystanders.GetCounters("bystander"), 3)

    def test_innocent_bystanders_can_be_paid_with_a_resource(self):
        def spend(prompt):
            option = option_named(prompt, "Spend_1_resource")
            return pick(option, [], payment_effect_ids(option)[:1])

        table, _ = self.innocent_bystanders(spend)

        main_scheme = table.world.area_schemes_main.Get()[0]
        self.assertEqual(main_scheme.threat, 0)
        self.assertEqual(len(table.player.hand_cards.Get()), 1)


if __name__ == "__main__":
    unittest.main()
