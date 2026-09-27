"""Wakanda Forever! resolves every Black Panther upgrade's special it can."""

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


class WakandaForeverTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def play(self, hero_damage):
        """Vibranium Suit (01049) and Panther Claws (01047) in play."""
        from game.world.world_render import WorldRender

        commands = [
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("01043a", "01088")',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.PutIntoPlay("01049")',
            'Puzzle.PutIntoPlay("01047")',
        ]
        if hero_damage:
            commands.append(f'Puzzle.Damage("Black Panther", {hero_damage})')
        seen = {"played": False}
        prompts = []

        def choose(prompt):
            prompts.append((prompt.event_name, [option.get("name") for option in prompt.options]))
            if len(prompts) > 20:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["played"]:
                    return None
                event = next(face for face in player.hand_cards.Get() if face.paper.card_id == "01043a")
                option = next(option for option in prompt.options
                              if option.get("bind_id") == event.card.object_id)
                seen.update(played=True, targets=list(option.get("all_legal_targets", [])),
                            range=list(option.get("target_num_range")),
                            rhino=world.FindCardsOnField(name="Rhino")[0])
                seen["rhino_health"] = seen["rhino"].health
                seen["hero_health"] = player.GetIdentity().health
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option),
                    [str(target) for target in seen["targets"]],
                    payment_effect_ids(option),
                )
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(Fixture("rhino", ("black_panther",), 5, tuple(commands)),
                               HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0, prompts)
        world = game.world
        suit = world.FindCardsOnField(name="Vibranium Suit")[0]
        claws = world.FindCardsOnField(name="Panther Claws")[0]
        return {
            "targets": sorted(seen["targets"]),
            "range": seen["range"],
            "suit": suit.card.object_id,
            "claws": claws.card.object_id,
            "rhino_damage": seen["rhino_health"] - seen["rhino"].health,
            "hero_healed": world.GetFirstPlayer().GetIdentity().health - seen["hero_health"],
        }

    def test_every_upgrade_must_be_resolved(self):
        result = self.play(3)

        # Both upgrades, and no fewer: the player cannot skip one.
        self.assertEqual(result["targets"], sorted([result["suit"], result["claws"]]))
        self.assertEqual(result["range"], [2, 2])
        # Vibranium Suit moves 1 damage, then Panther Claws deals 4 as the
        # final step.
        self.assertEqual(result["hero_healed"], 1)
        self.assertEqual(result["rhino_damage"], 5)

    def test_an_undamaged_hero_still_resolves_without_error(self):
        result = self.play(0)

        self.assertEqual(result["hero_healed"], 0)
        self.assertEqual(result["rhino_damage"], 4)

if __name__ == "__main__":
    unittest.main()
