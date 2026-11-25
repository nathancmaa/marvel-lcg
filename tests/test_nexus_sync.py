"""Cerebro's Nexus sync client against the real Nexus sync server.

    python -m unittest tests.test_nexus_sync

The server and Phoenix's import tool come from the marvel-lcg-phoenix
reference checkout: `../nexus-sync-ref` beside this repository, or
NEXUS_SYNC_REF. Without it these tests are skipped.
"""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.statistics.game_history import GameHistory, SYNC_COLUMNS
from game.statistics.nexus_sync import NexusSync, RecordId

ROOT = Path(__file__).resolve().parents[1]
REF = Path(os.environ.get('NEXUS_SYNC_REF', ROOT.parent / 'nexus-sync-ref'))
SECRET = 'test-secret-not-real'

if (REF / 'server' / 'nexus_sync' / 'server.py').exists():
    os.environ['NEXUS_SYNC_QUIET'] = '1'
    sys.path.insert(0, str(REF / 'server'))
    from nexus_sync import server as nexus_server  # noqa: E402
    _spec = importlib.util.spec_from_file_location(
        'sync_import_phoenix', REF / 'tools' / 'sync_import_phoenix.py')
    import_tool = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(import_tool)
else:
    nexus_server = None
    import_tool = None


def game(key, *, result='win', notes='', hero_rating=None, undo_count=0, **extra):
    """A history record for _store_game."""
    return {
        'source_key': key,
        'finished_at': extra.pop('finished_at', '2026-11-01T20:00:00+00:00'),
        'engine_version': '0.7.13.2',
        'rules_version': 'v18_all',
        'hero_code': '01001a',
        'hero_name': 'Spider-Man',
        'villain_code': '01094',
        'villain_name': 'Rhino',
        'scenario_name': 'Rhino',
        'scenario_key': 'rhino',
        'result': result,
        'rounds': 7,
        'playtime_seconds': 1234.5,
        'seed': 42,
        'undo_count': undo_count,
        'notes': notes,
        'hero_rating': hero_rating,
        **extra,
    }


@unittest.skipIf(nexus_server is None, f'no Nexus reference checkout at {REF}')
class NexusSyncTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server_db = str(self.root / 'sync.sqlite3')
        self.httpd = None
        self.start_server()

    def tearDown(self):
        self.stop_server()
        self.temp.cleanup()

    # --- fixtures ------------------------------------------------------------

    def start_server(self):
        started = threading.Event()
        holder = {}

        def ready(httpd):
            holder['httpd'] = httpd
            started.set()

        self.server_thread = threading.Thread(
            target=nexus_server.serve,
            args=(self.server_db, '127.0.0.1', 0, SECRET, ready),
            daemon=True,
        )
        self.server_thread.start()
        self.assertTrue(started.wait(10))
        self.httpd = holder['httpd']
        self.address = '127.0.0.1:%d' % self.httpd.server_address[1]

    def stop_server(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.server_thread.join(10)
            self.httpd = None

    def history(self, name):
        folder = self.root / name
        (folder / 'replays').mkdir(parents=True, exist_ok=True)
        history = GameHistory(
            file_path=str(folder / 'statistics.sqlite3'),
            replay_folders=[str(folder / 'replays')],
        )
        history.enabled = True
        history.Initialize()
        return history

    def client(self, history, address=None):
        return NexusSync(history, address or self.address, SECRET, timeout=5)

    def server_record(self, key):
        store = nexus_server.Store(self.server_db)
        try:
            rows = [c for c in store.sync([], 0, 5000)['changes'] if c['key'] == key]
        finally:
            store.close()
        return rows[0] if rows else None

    @staticmethod
    def folder_texts(client, folder):
        path = Path(client.state_folder) / folder
        return sorted(p.read_text(encoding='utf-8') for p in path.glob('*.json')) if path.exists() else []

    @staticmethod
    def achievements(history):
        with closing(sqlite3.connect(history.file_path)) as connection:
            return {row[0] for row in connection.execute('SELECT achievement_id FROM achievements')}

    # --- both ways ------------------------------------------------------------

    def test_two_clients_sync_both_ways(self):
        a_history, b_history = self.history('a'), self.history('b')
        a_history._store_game(
            game('game:a1', players=[
                {'seat': 0, 'hero_code': '01001a', 'hero_name': 'Spider-Man',
                 'deck_name': 'Web', 'deck_source': 'starter'},
                {'seat': 1, 'hero_code': '01010a', 'hero_name': 'Captain Marvel',
                 'deck_name': 'Cosmic', 'deck_source': 'marvelcdb'},
            ]),
            [{'card_id': '01002', 'card_name': 'Black Cat', 'damage_dealt': 3,
              'damage_taken': 0, 'thwarted_threat': 2, 'entered_play': 1}],
        )
        b_history._store_game(game('phoenix:b1', result='loss', notes='Kraven — très dur'))
        a, b = self.client(a_history), self.client(b_history)

        self.assertTrue(a.Sync())
        self.assertTrue(b.Sync())
        self.assertTrue(a.Sync())

        self.assertEqual(sorted(a_history.SyncRows()), ['game:a1', 'phoenix:b1'])
        self.assertEqual(a_history.SyncRows(), b_history.SyncRows())
        self.assertEqual(b.last_summary['pulled'], 1)
        self.assertEqual(a.last_summary['pulled'], 1)
        # The pulled win counts for B's achievements.
        self.assertIn('no_second_chances', self.achievements(b_history))
        # Settled: another round sends and takes nothing.
        self.assertTrue(a.Sync())
        self.assertTrue(b.Sync())
        self.assertEqual((a.last_summary['pushed'], a.last_summary['pulled']), (0, 0))
        self.assertEqual((b.last_summary['pushed'], b.last_summary['pulled']), (0, 0))

    def test_pulls_page_through_everything(self):
        a_history, b_history = self.history('a'), self.history('b')
        for n in range(7):
            a_history._store_game(game(f'game:page{n}', finished_at=f'2026-11-0{n + 1}T20:00:00+00:00'))
        a, b = self.client(a_history), self.client(b_history)
        a.PULL_LIMIT = b.PULL_LIMIT = 2
        self.assertTrue(a.Sync())
        self.assertTrue(b.Sync())  # a first sync: pulled page by page
        self.assertEqual(b_history.SyncRows(), a_history.SyncRows())
        b_history._store_game(game('game:page-b', finished_at='2026-11-09T20:00:00+00:00'))
        for n in range(3):
            a_history._store_game(game(f'game:more{n}', finished_at=f'2026-11-1{n}T20:00:00+00:00'))
        self.assertTrue(a.Sync())
        self.assertTrue(b.Sync())  # an ordinary sync: pushes, then pages
        self.assertTrue(a.Sync())
        self.assertEqual(len(b_history.SyncRows()), 11)
        self.assertEqual(b_history.SyncRows(), a_history.SyncRows())

    def test_a_pulled_replacement_keeps_the_text_it_replaced(self):
        a_history, b_history = self.history('a'), self.history('b')
        a_history._store_game(game('game:r1'))
        a, b = self.client(a_history), self.client(b_history)
        a.Sync()
        b.Sync()
        before = a_history.SyncRows()['game:r1']

        b_history.SaveGameRatings('game:r1', {'hero_rating': 4})
        self.assertTrue(b.Sync())
        self.assertTrue(a.Sync())

        self.assertIn('"hero_rating":4', a_history.SyncRows()['game:r1'])
        self.assertEqual(self.folder_texts(a, 'sync-conflicts'), [before])

    def test_the_background_loop_syncs_at_start_and_on_request(self):
        a_history, b_history = self.history('a'), self.history('b')
        a = self.client(a_history)
        a_history.on_change = a.Request
        b = self.client(b_history)
        a.Start()
        try:
            deadline = time.time() + 10
            while not a.last_ok and time.time() < deadline:
                time.sleep(0.05)
            self.assertTrue(a.last_ok)
            with mock.patch.object(GameHistory, '_should_record_live_game', return_value=True), \
                    mock.patch.object(GameHistory, '_live_record', return_value=game('game:live')), \
                    mock.patch.object(GameHistory, '_live_card_statistics', return_value=[]):
                a_history.RecordCompletedGame(object())
            deadline = time.time() + 10
            while self.server_record('game:live') is None and time.time() < deadline:
                time.sleep(0.05)
        finally:
            a.Stop()
        self.assertTrue(b.Sync())
        self.assertIn('game:live', b_history.SyncRows())

    # --- away and back ---------------------------------------------------------

    def test_a_game_played_offline_waits_in_the_outbox(self):
        a_history, b_history = self.history('a'), self.history('b')
        a, b = self.client(a_history), self.client(b_history)
        self.assertTrue(a.Sync())
        self.assertTrue(b.Sync())

        self.stop_server()
        a_history._store_game(game('game:away'))
        self.assertFalse(a.Sync())
        self.assertIn("can't be reached", a.status)
        self.assertEqual(a.Queued(), 1)

        # Cerebro restarts while away: the queue is on disk, stamp and all.
        stamped = json.loads((Path(a.state_folder) / NexusSync.OUTBOX_FILE).read_text())
        self.start_server()
        a = self.client(a_history)
        self.assertTrue(a.Sync())
        self.assertEqual(a.last_summary['pushed'], 1)
        self.assertEqual(a.Queued(), 0)
        record = self.server_record('game:away')
        self.assertEqual(record['hlc'], stamped[RecordId('game:away')]['hlc'])

        b = self.client(b_history)
        self.assertTrue(b.Sync())
        self.assertIn('game:away', b_history.SyncRows())

    # --- deletions -------------------------------------------------------------

    def test_a_deletion_reaches_the_other_device_and_leaves_a_copy(self):
        a_history, b_history = self.history('a'), self.history('b')
        saved = a_history.SavePhysicalGame({
            'finished_at': '2026-11-02', 'hero_code': '01001a', 'hero_name': 'Spider-Man',
            'villain_code': '01094', 'scenario_name': 'Rhino', 'result': 'win',
        })
        a, b = self.client(a_history), self.client(b_history)
        a.Sync()
        b.Sync()
        (key,) = b_history.SyncRows()
        text = b_history.SyncRows()[key]

        a_history.DeletePhysicalGame(saved['id'])
        self.assertTrue(a.Sync())
        self.assertTrue(self.server_record(key)['deleted'])
        self.assertTrue(b.Sync())

        self.assertEqual(b_history.SyncRows(), {})
        self.assertEqual(self.folder_texts(b, 'sync-trash'), [text])

    def test_losing_most_games_at_once_pulls_them_back_instead_of_deleting(self):
        a_history, b_history = self.history('a'), self.history('b')
        for n in range(6):
            a_history._store_game(game(f'game:loss{n}', finished_at=f'2026-11-0{n + 1}T20:00:00+00:00'))
        a, b = self.client(a_history), self.client(b_history)
        a.Sync()
        b.Sync()
        texts = a_history.SyncRows()

        with closing(sqlite3.connect(a_history.file_path)) as connection, connection:
            connection.execute('PRAGMA foreign_keys = ON')
            connection.execute("DELETE FROM games WHERE source_key != 'game:loss0'")
        self.assertTrue(a.Sync())

        self.assertEqual(a.last_summary['pushed'], 0)
        self.assertFalse(any(self.server_record(k)['deleted'] for k in texts))
        self.assertEqual(a_history.SyncRows(), texts)
        self.assertTrue(b.Sync())
        self.assertEqual(b_history.SyncRows(), texts)

    # --- the first sync ---------------------------------------------------------

    def test_first_sync_marks_equal_text_synced_without_sending_it(self):
        b_history = self.history('b')
        b_history._store_game(game('phoenix:same'))
        b_history._store_game(game('game:same', finished_at='2026-11-03T20:00:00+00:00'))
        b = self.client(b_history)
        self.assertTrue(b.Sync())
        before = {k: self.server_record(k) for k in ('phoenix:same', 'game:same')}
        (self.root / 'a').mkdir()
        b_history.BackupTo(str(self.root / 'a' / 'statistics.sqlite3'))
        a = self.client(self.history('a'))

        self.assertTrue(a.Sync())

        self.assertEqual((a.last_summary['pushed'], a.last_summary['pulled']), (0, 0))
        self.assertEqual({k: self.server_record(k) for k in before}, before)
        self.assertEqual(self.folder_texts(a, 'sync-conflicts'), [])

    def test_first_sync_takes_the_servers_text_for_a_phoenix_game(self):
        phoenix_history, a_history = self.history('phoenix'), self.history('a')
        phoenix_history._store_game(game('phoenix:p1', notes='rated on the phone', hero_rating=5))
        a_history._store_game(game('phoenix:p1', notes='old manual import'))
        local_text = a_history.SyncRows()['phoenix:p1']
        self.assertTrue(self.client(phoenix_history).Sync())
        server_text = self.server_record('phoenix:p1')['body']
        a = self.client(a_history)

        self.assertTrue(a.Sync())

        self.assertEqual(a_history.SyncRows()['phoenix:p1'], server_text)
        self.assertEqual(self.server_record('phoenix:p1')['body'], server_text)
        self.assertEqual(a.last_summary['pushed'], 0)
        self.assertEqual(self.folder_texts(a, 'sync-conflicts'), [local_text])

    def test_first_sync_keeps_cerebros_text_for_its_own_game_everywhere(self):
        other_history, a_history = self.history('other'), self.history('a')
        other_history._store_game(game('game:c1', notes='a stale copy'))
        a_history._store_game(game('game:c1', notes='the real game', hero_rating=3))
        cerebro_text = a_history.SyncRows()['game:c1']
        other_text = other_history.SyncRows()['game:c1']
        other = self.client(other_history)
        self.assertTrue(other.Sync())
        a = self.client(a_history)

        self.assertTrue(a.Sync())
        self.assertTrue(other.Sync())

        self.assertEqual(a.last_summary['pushed'], 1)
        self.assertEqual(self.server_record('game:c1')['body'], cerebro_text)
        self.assertEqual(a_history.SyncRows()['game:c1'], cerebro_text)
        self.assertEqual(other_history.SyncRows()['game:c1'], cerebro_text)
        # Nothing lost on either side: each kept the text it gave up.
        self.assertEqual(self.folder_texts(a, 'sync-conflicts'), [other_text])
        self.assertEqual(self.folder_texts(other, 'sync-conflicts'), [other_text])
        # And it stays settled.
        self.assertTrue(a.Sync())
        self.assertEqual((a.last_summary['pushed'], a.last_summary['pulled']), (0, 0))

    def test_first_sync_brings_back_a_cerebro_game_the_server_had_deleted(self):
        other_history, a_history = self.history('other'), self.history('a')
        other_history._store_game(game('game:gone'))
        other = self.client(other_history)
        other.Sync()
        with closing(sqlite3.connect(other_history.file_path)) as connection, connection:
            connection.execute("DELETE FROM games WHERE source_key = 'game:gone'")
        other.Sync()
        self.assertTrue(self.server_record('game:gone')['deleted'])
        a_history._store_game(game('game:gone', notes='still here'))
        a = self.client(a_history)

        self.assertTrue(a.Sync())

        self.assertIn('game:gone', a_history.SyncRows())
        self.assertFalse(self.server_record('game:gone')['deleted'])

    def test_first_sync_makes_one_backup_and_never_replaces_it(self):
        a_history = self.history('a')
        a_history._store_game(game('game:b1'))
        backup = Path(a_history.file_path).with_name('statistics.pre-nexus-sync.sqlite3')
        a = self.client(a_history)

        self.assertTrue(a.Sync())
        with closing(sqlite3.connect(backup)) as connection:
            self.assertEqual(connection.execute('SELECT source_key FROM games').fetchall(), [('game:b1',)])
        first = backup.read_bytes()
        a_history._store_game(game('game:b2', finished_at='2026-11-05T20:00:00+00:00'))
        self.assertTrue(a.Sync())
        self.assertEqual(backup.read_bytes(), first)

        # A device whose state was lost syncs "first" again; the backup stays.
        b_history = self.history('b')
        Path(b_history.file_path).with_name('statistics.pre-nexus-sync.sqlite3').write_bytes(b'kept')
        self.assertTrue(self.client(b_history).Sync())
        self.assertEqual(
            Path(b_history.file_path).with_name('statistics.pre-nexus-sync.sqlite3').read_bytes(), b'kept')

    def test_a_new_server_is_sent_everything_again(self):
        a_history = self.history('a')
        a_history._store_game(game('game:s1'))
        a = self.client(a_history)
        self.assertTrue(a.Sync())
        self.stop_server()
        os.remove(self.server_db)
        self.start_server()
        a.address = self.address

        self.assertTrue(a.Sync())

        self.assertEqual(self.server_record('game:s1')['body'], a_history.SyncRows()['game:s1'])

    # --- configuration ----------------------------------------------------------

    def test_without_an_address_or_secret_nothing_runs(self):
        a_history = self.history('a')
        self.assertIsNone(NexusSync.FromConfig(a_history))
        for address, secret in (('', SECRET), (self.address, '')):
            client = NexusSync(a_history, address, secret)
            self.assertFalse(client.Sync())
            client.Start()
            self.assertIsNone(client._thread)
        folder = Path(a_history.file_path).parent
        self.assertFalse((folder / NexusSync.STATE_FILE).exists())
        self.assertFalse((folder / 'statistics.pre-nexus-sync.sqlite3').exists())

    def test_a_wrong_secret_is_reported(self):
        client = NexusSync(self.history('a'), self.address, 'not-the-secret')
        self.assertFalse(client.Sync())
        self.assertEqual(client.status, 'The sync server refused the secret.')

    # --- Phoenix's text ---------------------------------------------------------

    def rich_history(self):
        """Games touching every column kind: NULLs, floats, seats, cards, Phoenix detail."""
        history = self.history('rich')
        history._store_game(
            game('phoenix:0a1b', notes='Ünïcödé “quotes” \\ and\nnew lines', hero_rating=5,
                 heroic=2, expert=1, remaining_hit_points=1, minions_in_play=0,
                 side_schemes_in_play=0, campaign_id='rise', game_mode='campaign',
                 players=[
                     {'seat': 0, 'hero_code': '01001a', 'hero_name': 'Spider-Man',
                      'deck_name': 'Deck ／ one', 'deck_source': 'starter'},
                     {'seat': 1, 'hero_code': '04001a', 'hero_name': 'Black Panther (Shuri)',
                      'deck_name': '', 'deck_source': ''},
                 ]),
            [
                {'card_id': '01002', 'card_name': 'Black Cat', 'damage_dealt': 0,
                 'damage_taken': 1, 'thwarted_threat': 4, 'entered_play': 1},
                {'card_id': '01001b', 'card_name': 'Peter Parker', 'damage_dealt': 9,
                 'damage_taken': 3, 'thwarted_threat': 0, 'entered_play': 0},
            ],
        )
        history._store_game(game(
            'game:nulls', result='unknown', finished_at='2026-10-01T09:00:00+00:00',
            rounds=None, playtime_seconds=None, seed=None, undo_count=None))
        history._store_game(game(
            'mct:2026-01-01-rhino', source='physical', finished_at='2026-01-01',
            playtime_seconds=60, is_service=1))
        # A replay-imported game: Cerebro's own replay columns stay out of the text.
        history._store_game(game(
            'replay:abc', source='replay_import', imported_from_replay=1,
            replay_analysis_status='done', replay_file='x.json',
            finished_at='2026-09-09T09:09:09+00:00'))
        with closing(sqlite3.connect(history.file_path)) as connection, connection:
            game_id = connection.execute(
                "SELECT id FROM games WHERE source_key = 'phoenix:0a1b'").fetchone()[0]
            connection.execute(
                'INSERT INTO phoenix_performance (game_id, data) VALUES (?, ?)',
                (game_id, json.dumps({'heroes': [{'seat': 0, 'code': '01001a', 'name': 'Spider-Man',
                                                  'totals': {'damage_dealt': 9, 'damage_taken': 3,
                                                             'threat_removed': 4, 'minions_defeated': 1},
                                                  'cards': []}]})),
            )
        return history

    def test_the_text_is_phoenixs_import_tools_byte_for_byte(self):
        self.assertEqual(list(SYNC_COLUMNS), import_tool.game_columns())
        history = self.rich_history()
        with closing(sqlite3.connect(history.file_path)) as connection:
            tool_rows = {key: text for key, _, text in import_tool.rows(connection, import_tool.game_columns())}
        self.assertEqual(history.SyncRows(), tool_rows)
        self.assertIn('"performance":{"heroes":', tool_rows['phoenix:0a1b'])
        self.assertIn('"playtime_seconds":60.0', tool_rows['mct:2026-01-01-rhino'])

    def test_a_synced_game_reads_back_as_the_same_text(self):
        source = self.rich_history()
        target = self.history('copy')
        texts = source.SyncRows()
        outcome = target.ApplySync([json.loads(t) for t in texts.values()], [])
        self.assertEqual(outcome['rejected'], [])
        self.assertEqual(target.SyncRows(), texts)
        # Applying it again replaces rather than adds.
        target.ApplySync([json.loads(t) for t in texts.values()], [])
        self.assertEqual(target.SyncRows(), texts)

    def test_games_the_import_tool_sent_are_not_sent_again(self):
        history = self.rich_history()
        games = import_tool.read_copy(history.file_path)
        added, lost = import_tool.push(self.address, SECRET, games)
        self.assertEqual((added, lost), (len(games), 0))
        client = self.client(history)

        self.assertTrue(client.Sync())
        self.assertEqual((client.last_summary['pushed'], client.last_summary['pulled']), (0, 0))
        self.assertEqual(client.Queued(), 0)
        self.assertTrue(client.Sync())
        self.assertEqual(client.last_summary['pushed'], 0)
        self.assertTrue(all(self.server_record(k)['device'] == 'import' for k in history.SyncRows()))


if __name__ == '__main__':
    unittest.main()
