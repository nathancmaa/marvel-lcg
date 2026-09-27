"""Godlike Stamina can be played just to discard a status card."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class GodlikeStaminaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_an_undamaged_stunned_hero_can_play_it_to_discard_the_stun(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", ("valkyrie",), 5, (
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("25024")',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.Stun("Valkyrie")',
        ))
        seen = {"played": False, "offered": False}
        prompts = []

        def choose(prompt):
            prompts.append(prompt.event_name)
            if len(prompts) > 20:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["played"]:
                    return None
                stamina = next(face for face in player.hand_cards.Get() if face.paper.card_id == "25024")
                option = next((option for option in prompt.options
                               if option.get("bind_id") == stamina.card.object_id), None)
                if option is None:
                    return None
                seen.update(played=True, offered=True, health=player.GetIdentity().health)
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option),
                    [str(player.GetIdentity().card.object_id)],
                    [],
                )
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        self.assertTrue(seen["offered"])
        identity = game.world.GetFirstPlayer().GetIdentity()
        self.assertFalse(identity.IsStunned())
        self.assertEqual(identity.health, seen["health"])


if __name__ == "__main__":
    unittest.main()
