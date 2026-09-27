"""A recorded choice that no longer fits its ask is dropped once, and only once.

Real games, run headlessly through the real controller. A quick save is
replayed with one recorded choice made not to fit, and the player's presses
at the ask put to them again are scripted: Redo there must not resubmit the
dropped choice, since each resubmission was dropped in turn and took the
next valid recorded choice with it. A recorded choice naming a card that is
not on the table must not fall back to its raw option number, which can name
a different option of this ask. And an empty answer to an ask that must be
answered -- Cancel on the discard down to hand size -- is asked again rather
than stopping the game with an error dialog.
"""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, HeadlessStatistics, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager

# The loader resolves paths against the working directory.
OPENING = 'unit_test/fixtures/saves/loki_x23_cable_opening.json'

# The Thwart recorded at this step of the opening.
MISFIT_STEP = 7


def replay_live(scene, devices):
    """Replay a recording as a live game would, where a misfit re-asks.

    Under test the controller asserts on a misfit instead, so this runs the
    game outside the test flag, as a player's Continue does.
    """
    from engine.job import JobManager
    from engine.log import Notify
    from game.game import Game
    from game.test import Test
    from game.world.world_render import WorldRender

    initialize_database()
    if not hasattr(JobManager, "condition"):
        JobManager.Initialize()
    statistics = HeadlessStatistics()
    game = Game(statistics, devices)
    notices: list = []
    errors: list = []
    with patch.object(Engine, 'statistics', statistics, create=True), \
            patch.object(Engine, 'game', game, create=True), \
            patch.object(Test, 'is_in_test', False), \
            patch.object(Notify, 'Command', side_effect=lambda text, *a, **k: notices.append(text)), \
            patch.object(WorldRender, 'ErrorOccurred', side_effect=lambda info, *a, **k: errors.append(info)), \
            contextlib.redirect_stdout(io.StringIO()):
        game.session.SetScene(scene, 'InTesting')
        game.GameSetup()
        game.GameLoop()
    return game, notices, errors


def load_opening():
    from game.scene.loader import LoaderHelper, SceneLoader

    scene = SceneLoader.Load(OPENING)
    LoaderHelper.EnsureSupportedReplay(scene)
    return scene


def recorded_ids(scene_or_replay) -> list:
    inputs = getattr(scene_or_replay, 'inputs', None)
    if inputs is None:
        inputs = scene_or_replay.replay_inputs
    return [op.effect.id for op in inputs]


class RecordedChoiceMisfitTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_redo_after_a_misfit_does_not_delete_the_next_recorded_choice(self):
        from game.cheat.cheat import Cheat

        scene = load_opening()
        original = recorded_ids(scene)
        # The recorded Thwart now names a target that is not on the table.
        scene.inputs[MISFIT_STEP].effect.targets = ['c999 99999']

        presses: list = []

        def press_redo_twice(prompt):
            game = Engine.game
            replay = game.controller_manager.replay
            presses.append((replay.current_step_id, recorded_ids(replay)))
            if len(presses) > 2:
                return None
            Cheat.PreDebugExec('/skip 0', game.world)
            return CommandDescriptor()

        devices = HeadlessDeviceManager(choice_provider=press_redo_twice)
        game, notices, errors = replay_live(scene, devices)

        expected = original[:MISFIT_STEP] + original[MISFIT_STEP + 1:]
        self.assertEqual(len(presses), 3)
        for step, recording in presses:
            # The ask is put again each time, at the same step, and the
            # recording keeps every choice after the dropped one.
            self.assertEqual(step, MISFIT_STEP)
            self.assertEqual(recording, expected)
        self.assertEqual(len(notices), 1)
        self.assertEqual(errors, [])
        self.assertEqual(recorded_ids(game.controller_manager.replay), expected)

    def test_an_unrestorable_recorded_choice_is_not_resolved_by_its_number(self):
        scene = load_opening()
        original = recorded_ids(scene)
        # A choice on a card that is not on the table cannot be mapped onto
        # this ask. Its number, 4, is this ask's Attack, and card 141 is the
        # Attack's one legal target: taken by number, it would attack unasked.
        scene.inputs[MISFIT_STEP].effect.id = 'e4 Thwart c999 99999'
        scene.inputs[MISFIT_STEP].effect.targets = ['c141 target']

        seen: list = []

        def stop(prompt):
            replay = Engine.game.controller_manager.replay
            seen.append((replay.current_step_id, [option['id'] for option in prompt.options]))
            return None

        devices = HeadlessDeviceManager(choice_provider=stop)
        game, notices, errors = replay_live(scene, devices)

        self.assertEqual(len(seen), 1)
        step, option_ids = seen[0]
        self.assertIn(4, option_ids)
        # Put to the player at its own step, not resolved as option 4.
        self.assertEqual(step, MISFIT_STEP)
        self.assertEqual(
            recorded_ids(game.controller_manager.replay),
            original[:MISFIT_STEP] + original[MISFIT_STEP + 1:],
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(errors, [])


class ForcedDiscardTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_cancel_on_the_discard_down_to_hand_size_asks_again(self):
        from game.world.world_render import WorldRender

        fixture = Fixture(
            "rhino",
            ("spider_man",),
            424244,
            tuple(['Puzzle.CreateHandCards("01002")'] * 9),
        )
        discards: list = []

        def play(prompt):
            if 'WhenPlayerInTurn' in prompt.event_name:
                return CommandDescriptor()  # End Turn
            if prompt.event_name == 'End Turn' and prompt.options:
                minimum = prompt.options[0]['target_num_range'][0]
                if minimum == 0:
                    return CommandDescriptor()
                discards.append(prompt)
                if len(discards) == 1:
                    return CommandDescriptor()  # what Cancel posts
                return None
            return HeadlessDeviceManager._DefaultChoice(prompt)

        errors: list = []
        devices = HeadlessDeviceManager(choice_provider=play)
        with patch.object(WorldRender, 'ErrorOccurred', side_effect=lambda info, *a, **k: errors.append(info)), \
                contextlib.redirect_stdout(io.StringIO()):
            run_fixture(fixture, devices)

        self.assertEqual(errors, [])
        self.assertEqual(len(discards), 2)
        first, second = discards
        self.assertFalse(first.show_cancel)
        self.assertEqual(first.options, second.options)


if __name__ == "__main__":
    unittest.main()
