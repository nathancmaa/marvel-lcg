"""Saved games from real play replay to the end of their recording without
the engine reporting an error.

Each fixture is a quick save that once broke: the first had Seduced, an
Enchantress attachment, asking who "you" is and getting an assertion every
time a card was checked; the second is the opening of a two-handed Loki game
that stalled after an undo. Neither reaches a game outcome -- they are
saves, not finished games -- so what is asserted is that the recording is
played through whole, and cleanly.
"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine
from cards.database import CardsDB
from engine.lib.version import Ver
from engine.log import Log
from game.statistics.replay_outcome_analyzer import (
    ReplayOutcomeAnalysisError,
    ReplayOutcomeAnalyzer,
)

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'saves'


class SavedGameReplayTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def replay_whole(self, name: str) -> None:
        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False
        statistics.pause = True
        Log.log_statistics.clear()
        with patch.object(Engine, 'statistics', statistics, create=True):
            with self.assertRaises(ReplayOutcomeAnalysisError) as caught:
                ReplayOutcomeAnalyzer(statistics).Analyze(str(FIXTURES / name))
        # The recording runs out; it does not diverge, and nothing errors.
        self.assertIn('inputs ended', str(caught.exception))
        self.assertFalse(Log.HasError(error=True))

    def test_seduced_on_a_hero_no_longer_asks_who_you_is(self):
        self.replay_whole('loki_cable_x23_seduced.json')

    def test_the_two_handed_loki_opening_replays_whole(self):
        self.replay_whole('loki_x23_cable_opening.json')


if __name__ == '__main__':
    unittest.main()
