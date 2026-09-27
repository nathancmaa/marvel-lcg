"""Enchantress III in a real expert game: Future of Despair and charm counters."""

import contextlib
import io
import unittest

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


def play_with_console(fixture, commands):
    """Play a fixture, issuing one debug command at each of the player's turns.

    A command may be a string or a callable taking the world. The game stops at
    the first player turn after the last command has run.
    """
    queue = list(commands)

    def provider(prompt):
        if "WhenPlayerInTurn" in prompt.event_name:
            if not queue:
                return None
            world = Engine.game.world
            command = queue.pop(0)
            if callable(command):
                command = command(world)
            Engine.game.controller_manager.console.SetCommand(command, world)
            return CommandDescriptor()
        return HeadlessDeviceManager._DefaultChoice(prompt)

    devices = HeadlessDeviceManager(choice_provider=provider)
    with contextlib.redirect_stdout(io.StringIO()):
        game = run_fixture(fixture, devices)
    return game


def find_on_field(world, card_id):
    return [face for face in world.FindCardsOnField() if face.paper.card_id == card_id]


def villain_id(world):
    return world.GetScenario().area_villain.Get()[0].card.object_id


class EnchantressStageThreeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_stage_three_puts_future_of_despair_into_play_with_four_per_hero(self):
        fixture = Fixture("enchantress_expert", ("spider_man",), 5150)
        game = play_with_console(fixture, [
            # The first hit only removes stage II's tough status.
            lambda world: f"Puzzle.Damage({villain_id(world)}, 1)",
            lambda world: f"Puzzle.Damage({villain_id(world)}, 16)",
        ])
        world = game.world

        self.assertTrue(find_on_field(world, "55003"))
        future = find_on_field(world, "55006")
        self.assertEqual(len(future), 1)
        # Starting threat 2 per hero, plus an additional 4 per hero.
        self.assertEqual(future[0].threat, 6)
        # It is put into play, not revealed, so its When Revealed charm
        # counter is not placed.
        gaze = find_on_field(world, "55007a")
        self.assertEqual(gaze[0].GetCounters("charm"), 0)

    def test_stage_three_places_a_charm_counter_after_it_attacks_you(self):
        # Alluring Call, which has no boost icons or boost ability, is the
        # boost card, so the only charm counter comes from Enchantress III.
        fixture = Fixture(
            "enchantress_expert",
            ("spider_man",),
            5150,
            ('Puzzle.CreateEncounterDeck("55012")',),
        )
        game = play_with_console(fixture, [
            # The first hit only removes stage II's tough status.
            lambda world: f"Puzzle.Damage({villain_id(world)}, 1)",
            lambda world: f"Puzzle.Damage({villain_id(world)}, 16)",
            lambda world: f"Puzzle.DoAttack({villain_id(world)})",
        ])
        world = game.world

        self.assertTrue(find_on_field(world, "55003"))
        gaze = find_on_field(world, "55007a")
        self.assertEqual(gaze[0].GetCounters("charm"), 1)


if __name__ == "__main__":
    unittest.main()
