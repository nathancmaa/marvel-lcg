"""Two-Gun Kid's second target must be a different enemy."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class TwoGunKidTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_second_target_excludes_the_first_and_both_take_damage(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", ("spider_man",), 5, (
            'Puzzle.ClearHand()',
            'Puzzle.PutIntoPlay("56010")',
            'Puzzle.PutIntoPlay("01110")',
        ))
        seen = {"attacked": False}
        prompts = []

        def choose(prompt):
            prompts.append(prompt.event_name)
            if len(prompts) > 30:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["attacked"]:
                    return None
                kid = world.FindCardsOnField(name="Two-Gun Kid")[0]
                rhino = world.FindCardsOnField(name="Rhino")[0]
                minion = next(face for face in world.GetFirstPlayer().engaged_minions.Get())
                seen.update(rhino=rhino, minion=minion,
                            rhino_health=rhino.health, minion_health=minion.health)
                option = next(option for option in prompt.options
                              if option.get("name") == "Attack"
                              and option.get("bind_id") == kid.card.object_id)
                seen["attacked"] = True
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option), [str(rhino.card.object_id)], [])
            for option in prompt.options:
                bound = world.object_manager.card_dict.get(option.get("bind_id"))
                if bound and bound.face.paper.card_id == "56010" and \
                    prompt.event_name == "WhenUnitWouldAttack":
                    seen["second_targets"] = [int(target) for target in option.get("all_legal_targets", [])]
                    return CommandDescriptor(
                        HeadlessDeviceManager._DescriptorId(option),
                        [str(seen["minion"].card.object_id)],
                        [],
                    )
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        self.assertEqual(seen["second_targets"], [seen["minion"].card.object_id])
        self.assertEqual(seen["rhino_health"] - seen["rhino"].health, 2)
        self.assertFalse(seen["minion"].IsInPlay() and
                         seen["minion_health"] == seen["minion"].health)


if __name__ == "__main__":
    unittest.main()
