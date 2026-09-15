"""Undo waits for the last undo to land, redo needs something recorded ahead,
and a fresh choice after an undo takes its recording's place and keeps the rest."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from engine.controller.module.replay import InputModule
from game.cheat.cheat import Cheat


def recorded(effect_id, targets=(), resources=()):
    """A recorded choice, as the replay compares them."""
    return SimpleNamespace(
        id=effect_id,
        effect=SimpleNamespace(id=effect_id, targets=list(targets), resources=list(resources)),
    )


def fake_game(*, is_skipping=False, skip_to=0, current=10, replay_step=10, recorded=10):
    replay = SimpleNamespace(
        current_step_id=current,
        replay_step_id=replay_step,
        GetReplayOperationLen=lambda: recorded,
    )
    controller_manager = SimpleNamespace(
        skip=SimpleNamespace(is_skipping=is_skipping, skip_to=skip_to),
        replay=replay,
        undo=SimpleNamespace(last_step=8),
    )
    return SimpleNamespace(
        controller_manager=controller_manager,
        session=Mock(),
        scene=Mock(step=[]),
    )


class UndoRedoGuardTests(unittest.TestCase):

    def test_undo_waits_while_the_last_undo_is_still_replaying(self):
        # Mid-replay the checkpoints belong to the replay in progress; a
        # second press then jumped turns rather than one action.
        for game in (fake_game(is_skipping=True), fake_game(skip_to=12, current=6)):
            with patch.object(Engine, 'game', game, create=True):
                self.assertTrue(Cheat.PreDebugExec('/undo auto', None))
            game.session.Undo.assert_not_called()
            game.session.SkipTo.assert_not_called()

    def test_undo_goes_back_one_ask_once_the_table_is_settled(self):
        game = fake_game()
        with patch.object(Engine, 'game', game, create=True):
            self.assertTrue(Cheat.PreDebugExec('/undo auto', None))
        # last_step 8 from step 10: two steps back through the session.
        game.session.Undo.assert_called_once_with(2)

    def test_redo_with_nothing_recorded_ahead_does_nothing(self):
        # It used to feed the ask an empty answer, which on your own turn
        # is End Turn.
        game = fake_game(replay_step=10, recorded=10)
        with patch.object(Engine, 'game', game, create=True):
            self.assertTrue(Cheat.PreDebugExec('/skip 0', None))
        game.session.SkipTo.assert_not_called()

        ahead = fake_game(replay_step=10, recorded=12)
        with patch.object(Engine, 'game', ahead, create=True):
            self.assertTrue(Cheat.PreDebugExec('/skip 0', None))
        ahead.session.SkipTo.assert_called_once_with(10)

    def test_a_quick_load_is_a_live_game_for_continue_and_the_autosave(self):
        game = fake_game()
        game.active_session_enabled = False
        with patch.object(Engine, 'game', game, create=True):
            self.assertTrue(Cheat.PreDebugExec('/load save_1.json:-1', None))
        game.session.Load.assert_called_once()
        self.assertTrue(game.active_session_enabled)

    def test_the_same_choice_made_again_after_an_undo_keeps_the_recording(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=False, skip_to=0))
        replay = InputModule(manager)
        old = [recorded(f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        replay.current_step_id = 2
        replay.replay_step_id = 2
        again = recorded('old2')

        replay.Push(again)

        # Redo can carry on with what was recorded after it.
        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1', 'old2', 'old3', 'old4'])
        self.assertIs(replay.replay_inputs[2], again)
        self.assertEqual(replay.replay_step_id, 3)

    def test_a_different_choice_after_an_undo_drops_the_old_path(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=False, skip_to=0))
        replay = InputModule(manager)
        old = [recorded(f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        replay.current_step_id = 2
        replay.replay_step_id = 2
        fresh = recorded('fresh')

        replay.Push(fresh)

        # What was recorded beyond belongs to the old path: replayed, it
        # stopped the next undo short and fed Redo choices for a table that
        # no longer existed.
        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1', 'fresh'])
        self.assertEqual(replay.history_inputs, [fresh])
        self.assertEqual(replay.current_step_id, 3)

    def test_a_dropped_misfit_makes_room_for_the_answer_in_its_place(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=False, skip_to=0))
        replay = InputModule(manager)
        old = [recorded(f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        replay.current_step_id = 2
        replay.replay_step_id = 2

        # The recorded choice at step 2 did not fit the ask and is dropped;
        # what was recorded after it moves up, ready for Redo.
        self.assertTrue(replay.DropMisfit())
        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1', 'old3', 'old4'])

        # The player's answer goes in where the misfit was, not over old3.
        replay.Push(recorded('answer'))
        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1', 'answer', 'old3', 'old4'])
        self.assertEqual(replay.replay_step_id, 3)

        # A different choice at the next step is a new path from there.
        replay.Push(recorded('next'))
        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1', 'answer', 'next'])

        # Nothing to drop past the end of the recording.
        replay.replay_step_id = 9
        self.assertFalse(replay.DropMisfit())

    def test_a_replayed_input_keeps_the_recording(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True, skip_to=4))
        replay = InputModule(manager)
        old = [recorded(f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        replay.current_step_id = 2
        replay.replay_step_id = 2

        replay.Push(old[2])

        self.assertEqual(len(replay.replay_inputs), 5)


if __name__ == '__main__':
    unittest.main()
