"""Coup de Grace adds 3 damage and overkill to any attack, events included."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


def payment_effect_ids(option):
    effects = []
    for payment in option.get("target_payment", {}).values():
        for entry in payment.get("payment", []):
            effects.extend(str(effect_id) for effect_id in entry)
    return effects


class CoupDeGraceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_an_attack_event_deals_three_more_damage(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", ("spider_man",), 5, (
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("01005", "01088", "01088", "01088")',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.PutIntoPlay("32176")',
        ))
        seen = {"played": False, "coup": False}

        prompts = []

        def choose(prompt):
            prompts.append((prompt.event_name, [option.get("name") for option in prompt.options]))
            if len(prompts) > 30:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["played"]:
                    return None
                kick = next(face for face in player.hand_cards.Get() if face.paper.card_id == "01005")
                option = next(option for option in prompt.options
                              if option.get("bind_id") == kick.card.object_id)
                seen["played"] = True
                rhino = world.FindCardsOnField(name="Rhino")[0]
                seen["health_before"] = rhino.health
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option),
                    [str(rhino.card.object_id)],
                    payment_effect_ids(option),
                )
            for option in prompt.options:
                bound = world.object_manager.card_dict.get(option.get("bind_id"))
                if bound and bound.face.paper.card_id == "32176":
                    seen["coup"] = True
                    return CommandDescriptor(
                        HeadlessDeviceManager._DescriptorId(option),
                        [str(target) for target in option.get("all_legal_targets", [])[:1]],
                        [],
                    )
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        self.assertTrue(seen["coup"])
        rhino = game.world.FindCardsOnField(name="Rhino")[0]
        # Swinging Web Kick deals 8; Coup de Grace adds 3.
        self.assertEqual(seen["health_before"] - rhino.health, 11)
        self.assertEqual(game.world.FindCardsOnField(name="Coup de Grâce"), [])


if __name__ == "__main__":
    unittest.main()
