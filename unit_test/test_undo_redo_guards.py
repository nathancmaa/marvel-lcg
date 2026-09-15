"""Undo waits for the last undo to land, redo needs something recorded ahead,
and a fresh choice after an undo drops the recording it departs from."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from engine.controller.module.replay import InputModule
from game.cheat.cheat import Cheat


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

    def test_a_new_choice_after_an_undo_drops_the_old_recording(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=False, skip_to=0))
        replay = InputModule(manager)
        old = [SimpleNamespace(id=f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        # Undone back to step 2, and now the player chooses something new.
        replay.current_step_id = 2
        replay.replay_step_id = 2
        fresh = SimpleNamespace(id='fresh')

        replay.Push(fresh)

        self.assertEqual([op.id for op in replay.replay_inputs], ['old0', 'old1'])
        self.assertEqual(replay.history_inputs, [fresh])
        self.assertEqual(replay.current_step_id, 3)

    def test_a_replayed_input_keeps_the_recording(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True, skip_to=4))
        replay = InputModule(manager)
        old = [SimpleNamespace(id=f'old{i}') for i in range(5)]
        replay.SetReplayInputs(old)
        replay.current_step_id = 2
        replay.replay_step_id = 2

        replay.Push(old[2])

        self.assertEqual(len(replay.replay_inputs), 5)


if __name__ == '__main__':
    unittest.main()
