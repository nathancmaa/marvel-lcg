"""Resigning ends the game now, as a loss, from outside the game's own thread."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.cheat.cheat import Cheat
from game.game_run.game_session import GameSession
from game.world.game_over import GAME_OVER_REASON_MAP


class ResignTests(unittest.TestCase):

    def session(self) -> GameSession:
        return GameSession(SimpleNamespace())

    def test_a_resignation_is_a_loss(self):
        self.assertIs(GAME_OVER_REASON_MAP['The players resigned'], False)

    def test_resigning_holds_the_request_and_wakes_the_game_thread(self):
        session = self.session()
        with patch.object(GameSession, 'ExitWait') as exit_wait:
            session.Resign()
        self.assertTrue(session.resign_requested)
        exit_wait.assert_called_once_with()

    def test_the_game_thread_ends_the_game_once_and_only_while_it_runs(self):
        session = self.session()
        world = SimpleNamespace(is_game_over=False, game_over=Mock())

        self.assertFalse(session.ConsumeResignation(world))
        world.game_over.SetResigned.assert_not_called()

        with patch.object(GameSession, 'ExitWait'):
            session.Resign()
        self.assertTrue(session.ConsumeResignation(world))
        world.game_over.SetResigned.assert_called_once_with()
        # Consumed: the next ask does not end the next game.
        self.assertFalse(session.resign_requested)
        self.assertFalse(session.ConsumeResignation(world))

        # A game already over has nothing left to resign.
        with patch.object(GameSession, 'ExitWait'):
            session.Resign()
        over = SimpleNamespace(is_game_over=True, game_over=Mock())
        self.assertFalse(session.ConsumeResignation(over))
        over.game_over.SetResigned.assert_not_called()

    def test_a_new_scene_forgets_a_resignation_that_was_never_taken(self):
        session = self.session()
        session.game = SimpleNamespace(state=SimpleNamespace(SetStartState=lambda state: None))
        with patch.object(GameSession, 'ExitWait'):
            session.Resign()
        scene = SimpleNamespace(GetMetadataInt=lambda key: 0, version='0.7.12')
        with patch('game.game_run.game_session.Ver', lambda version: version):
            session.SetScene(scene, 'New')
        self.assertFalse(session.resign_requested)

    def test_the_resign_command_reaches_the_session_without_a_cheat_mark(self):
        # The same channel as /undo and /restart: handled before the command
        # could be written into the replay, so the game stays eligible for
        # the history, which is the whole point of resigning rather than
        # closing the tab.
        fake_game = SimpleNamespace(session=Mock())
        with patch.object(Engine, 'game', fake_game, create=True):
            self.assertTrue(Cheat.PreDebugExec('/resign', None))
        fake_game.session.Resign.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
