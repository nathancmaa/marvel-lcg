"""Suit Up finds an ally, an attachable upgrade, or both, whichever exist."""

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


class SuitUpTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def play_suit_up(self, discard_pile=()):
        from game.card.face import Ally, Upgrade
        from game.world.world_render import WorldRender

        commands = [
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("45017", "01088", "01088")',
        ]
        if discard_pile:
            commands.append(
                'Puzzle.CreatePlayerDiscardPile(%s)' % ", ".join(f'"{card}"' for card in discard_pile))
        # Spider-Man's starter deck has allies but no upgrade that attaches
        # to an ally; Inspired (01074) is one.
        fixture = Fixture("rhino", ("spider_man",), 11, tuple(commands))
        seen = {"played": False}

        def choose(prompt):
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["played"]:
                    seen["hand"] = sorted(face.paper.card_id for face in player.hand_cards.Get())
                    return None
                suit_up = next(face for face in player.hand_cards.Get() if face.paper.card_id == "45017")
                option = next(option for option in prompt.options
                              if option.get("bind_id") == suit_up.card.object_id)
                seen["played"] = True
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option), [], payment_effect_ids(option))
            if prompt.event_name == "WhenPlayerChooseAbility" and "range" not in seen:
                option = prompt.options[0]
                faces = [world.object_manager.card_dict[int(target)].face
                         for target in option.get("all_legal_targets", [])]
                allies = [face for face in faces if Ally.IsType(face)]
                upgrades = [face for face in faces if Upgrade.IsType(face)]
                seen["range"] = list(option.get("target_num_range"))
                seen["upgrades"] = sorted(face.paper.card_id for face in upgrades)
                picked = allies[:1] + upgrades[:1]
                seen["picked"] = sorted(face.paper.card_id for face in picked)
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option),
                    [str(face.card.object_id) for face in picked],
                    [],
                )
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))
        self.assertEqual(error.call_count, 0)
        return seen

    def test_an_ally_alone_is_found_when_no_upgrade_can_attach_to_one(self):
        seen = self.play_suit_up()

        self.assertEqual(seen["range"], [1, 2])
        self.assertEqual(seen["upgrades"], [])
        self.assertEqual(len(seen["picked"]), 1)
        self.assertIn(seen["picked"][0], seen["hand"])

    def test_an_ally_and_an_attachable_upgrade_are_both_found(self):
        seen = self.play_suit_up(discard_pile=("01074",))

        self.assertEqual(seen["range"], [2, 2])
        self.assertEqual(seen["upgrades"], ["01074"])
        for card_id in seen["picked"]:
            self.assertIn(card_id, seen["hand"])


if __name__ == "__main__":
    unittest.main()
