"""Starred decks are stored on the server, so every browser sees the same list.

They began in localStorage, which meant a deck starred on the laptop was not
starred on the phone against the same container. These are the assertions that
say the list is now shared, survives a restart, and cannot be filled with
anything a deck id is not.
"""

from pathlib import Path
import tempfile
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.statistics.game_history import GameHistory


class FavoriteDeckTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.history = self.open_history()
        self.assertTrue(self.history.available, 'game history did not start')

    def tearDown(self):
        self.history.Close()
        self.temp_dir.cleanup()

    def open_history(self):
        history = GameHistory(
            file_path=str(self.root / 'statistics.sqlite3'),
            replay_folders=[],
        )
        history.enabled = True
        history.Initialize()
        return history

    def reopen(self):
        """A second GameHistory over the same file, as a restart would be."""
        self.history.Close()
        self.history = self.open_history()
        return self.history

    def test_a_new_database_starts_with_no_favourites(self):
        self.assertEqual(self.history.GetFavoriteDecks(), [])

    def test_saved_favourites_come_back(self):
        self.history.SaveFavoriteDecks(['cable', 'decklist-31020'])
        self.assertEqual(
            self.history.GetFavoriteDecks(), ['cable', 'decklist-31020'])

    def test_favourites_survive_a_restart(self):
        """The point of the exercise: the list outlives the browser that set it."""
        self.history.SaveFavoriteDecks(['spider_man', 'deck-577'])
        self.assertEqual(
            self.reopen().GetFavoriteDecks(), ['spider_man', 'deck-577'])

    def test_saving_replaces_the_list(self):
        self.history.SaveFavoriteDecks(['cable', 'rogue'])
        self.history.SaveFavoriteDecks(['rogue'])
        self.assertEqual(self.history.GetFavoriteDecks(), ['rogue'])

    def test_a_deck_starred_twice_is_listed_once(self):
        result = self.history.SaveFavoriteDecks(['cable', 'cable'])
        self.assertEqual(result['favorite_decks'], ['cable'])
        self.assertEqual(self.history.GetFavoriteDecks(), ['cable'])

    def test_the_order_a_list_was_built_in_survives_later_saves(self):
        """A deck keeps the moment it was first starred.

        Otherwise every save restamps the whole list and the order becomes
        whatever the browser happened to send.
        """
        self.history.SaveFavoriteDecks(['cable'])
        self.history.SaveFavoriteDecks(['rogue', 'cable'])
        self.assertEqual(self.history.GetFavoriteDecks(), ['cable', 'rogue'])

    def test_an_id_that_is_not_a_deck_id_is_refused(self):
        for value in ['', '   ', 'a' * 121, 'has space', 'semi;colon', '../etc']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.history.SaveFavoriteDecks([value])

    def test_a_list_is_required(self):
        for value in ['cable', None, {'cable': True}, 7]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.history.SaveFavoriteDecks(value)

    def test_a_refused_save_leaves_the_stored_list_alone(self):
        self.history.SaveFavoriteDecks(['cable'])
        with self.assertRaises(ValueError):
            self.history.SaveFavoriteDecks(['cable', 'not a deck id'])
        self.assertEqual(self.history.GetFavoriteDecks(), ['cable'])


if __name__ == '__main__':
    unittest.main()
