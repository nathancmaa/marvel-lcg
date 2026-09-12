"""A two-handed game counts for both heroes, and still counts as one game.

Two-handed is one person playing two heroes from one screen. The decision it
turns on is that a win belongs to both of them: Cable and Spider-Man each beat
Rhino that night, and the coverage grid should say so on both rows.

What must not double is the game itself. One evening at the table is one game
played, one win, one entry in the recent list -- so the game keeps its own row
and who was in it lives beside it.
"""

from pathlib import Path
import tempfile
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.statistics.game_history import GameHistory


class TwoHandedHistoryTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.history = GameHistory(
            file_path=str(self.root / 'statistics.sqlite3'),
            replay_folders=[],
        )
        self.history.enabled = True
        self.history.Initialize()

    def tearDown(self):
        self.history.Close()
        self.temp_dir.cleanup()

    def store(self, key, result='win', players=None, **columns):
        """A finished game, through the same path a real one takes."""
        record = {
            'source_key': key,
            'finished_at': '2026-09-09T20:00:00Z',
            'hero_code': '40001a',
            'hero_name': 'Cable',
            'villain_code': '01001',
            'villain_name': 'Rhino',
            'scenario_name': 'Rhino',
            'scenario_key': 'rhino',
            'deck_name': 'Cable',
            'result': result,
        }
        record.update(columns)
        if players is not None:
            record['players'] = players
        return self.history._store_game(record)

    def two_handed(self, key, result='win'):
        return self.store(key, result=result, players=[
            {'seat': 0, 'hero_code': '40001a', 'hero_name': 'Cable',
             'deck_name': 'Cable'},
            {'seat': 1, 'hero_code': '01001a', 'hero_name': 'Spider-Man',
             'deck_name': 'Spider-Man'},
        ])

    def hero_row(self, rows, code):
        return next((row for row in rows if row['hero_code'] == code), None)

    def test_a_solo_game_still_records_one_hero(self):
        self.store('solo:1')
        heroes = self.history.GetDashboard('all')['heroes']
        self.assertEqual(len(heroes), 1)
        self.assertEqual(heroes[0]['hero_code'], '40001a')
        self.assertEqual(heroes[0]['games'], 1)

    def test_a_two_handed_win_counts_for_both_heroes(self):
        self.two_handed('two:1')
        heroes = self.history.GetDashboard('all')['heroes']
        self.assertEqual(
            {row['hero_code'] for row in heroes}, {'40001a', '01001a'})
        for code in ('40001a', '01001a'):
            with self.subTest(hero=code):
                row = self.hero_row(heroes, code)
                self.assertEqual(row['games'], 1)
                self.assertEqual(row['wins'], 1)

    def test_a_two_handed_game_is_still_one_game(self):
        """The overview counts evenings, not heroes."""
        self.two_handed('two:1')
        overview = self.history.GetDashboard('all')['overview']
        self.assertEqual(overview['completed'], 1)
        self.assertEqual(overview['wins'], 1)
        self.assertEqual(
            len(self.history.GetDashboard('all')['recent_games']), 1)

    def test_the_coverage_grid_marks_the_pairing_for_both(self):
        """The reason the decision matters: two squares light, not one."""
        self.two_handed('two:1')
        counts = {
            (row['hero_code'], row['scenario_key']): row
            for row in self.history.GetMatchupCounts('all')
        }
        for code in ('40001a', '01001a'):
            with self.subTest(hero=code):
                row = counts.get((code, 'rhino'))
                self.assertIsNotNone(row, 'the pairing is missing')
                self.assertEqual(row['wins'], 1)
                self.assertEqual(row['best_beaten'], 1)

    def test_a_two_handed_loss_counts_against_both(self):
        self.two_handed('two:loss', result='loss')
        heroes = self.history.GetDashboard('all')['heroes']
        for code in ('40001a', '01001a'):
            with self.subTest(hero=code):
                row = self.hero_row(heroes, code)
                self.assertEqual(row['wins'], 0)
                self.assertEqual(row['losses'], 1)

    def test_each_deck_in_a_two_handed_game_keeps_its_own_record(self):
        self.two_handed('two:1')
        decks = {row['deck_name']: row for row in
                 self.history.GetDeckRecords('all')['decks']}
        self.assertEqual(sorted(decks), ['Cable', 'Spider-Man'])
        self.assertEqual(decks['Cable']['wins'], 1)
        self.assertEqual(decks['Spider-Man']['wins'], 1)

    def test_a_game_recorded_before_seats_existed_still_has_one(self):
        """A record with no players named is a game from before there were two."""
        self.store('legacy:1')
        heroes = self.history.GetDashboard('all')['heroes']
        self.assertEqual(len(heroes), 1)
        self.assertEqual(heroes[0]['hero_code'], '40001a')

    def test_the_recent_list_names_every_seat(self):
        self.two_handed('two')
        self.store('one')

        rows = {row['source_key'] if 'source_key' in row.keys() else row['id']: row
                for row in self.history.GetDashboard()['recent_games']}
        by_key = {row['hero_name']: row for row in rows.values()}
        two = next(row for row in rows.values() if row['seats'] == 2)
        self.assertEqual(two['heroes'], 'Cable／Spider-Man')
        self.assertEqual(two['decks'], 'Cable／Spider-Man')
        one = next(row for row in rows.values() if row['seats'] == 1)
        self.assertEqual(one['heroes'], 'Cable')
        self.assertIn('Cable', by_key)

    def test_storing_the_same_game_twice_does_not_double_its_seats(self):
        self.two_handed('two:1')
        self.two_handed('two:1')
        heroes = self.history.GetDashboard('all')['heroes']
        for code in ('40001a', '01001a'):
            with self.subTest(hero=code):
                self.assertEqual(self.hero_row(heroes, code)['games'], 1)


if __name__ == '__main__':
    unittest.main()
