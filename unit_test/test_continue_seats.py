"""Continue opens a two-handed game as a hot seat, so both seats connect."""
import json
import os
import tempfile
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.game import Game


class ContinueSeatsTests(unittest.TestCase):

    def saved(self, players):
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump({'players': players, 'inputs': []}, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_a_two_handed_save_seats_two(self):
        self.assertEqual(Game.SeatsInSavedGame(self.saved([{'name': 'X-23'}, {'name': 'Cable'}])), 2)

    def test_a_solo_save_seats_one(self):
        self.assertEqual(Game.SeatsInSavedGame(self.saved([{'name': 'Cable'}])), 1)

    def test_a_file_that_cannot_say_seats_one(self):
        self.assertEqual(Game.SeatsInSavedGame('does-not-exist.json'), 1)
        self.assertEqual(Game.SeatsInSavedGame(self.saved([])), 1)


if __name__ == '__main__':
    unittest.main()
