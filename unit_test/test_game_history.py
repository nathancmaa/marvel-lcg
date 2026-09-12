from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.statistics.achievements import ACHIEVEMENTS
from game.statistics.game_history import GameHistory
from game.statistics.replay_outcome_analyzer import ReplayOutcome
from game.scene.scene import Scene


class GameHistoryTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.replay_folder = self.root / 'replays'
        self.replay_folder.mkdir()
        self.history = GameHistory(
            file_path=str(self.root / 'statistics.sqlite3'),
            replay_folders=[str(self.replay_folder)],
        )
        self.history.enabled = True
        self.history.Initialize()

    def tearDown(self):
        self.history.Close()
        self.temp_dir.cleanup()

    def record(
        self,
        key,
        *,
        hero='Spider-Man',
        hero_code='01001a',
        villain='Rhino',
        villain_code='01094',
        expert=False,
        result='win',
        remaining_hit_points=None,
        minions_in_play=None,
        side_schemes_in_play=None,
        undo_count=None,
        source='digital',
        is_service=False,
    ):
        return self.history._store_game({
            'source_key': f'test:{key}',
            'finished_at': f'2026-08-10T12:{key % 60:02d}:00+00:00',
            'engine_version': '0.6.0.0',
            'rules_version': 'v18',
            'hero_code': hero_code,
            'hero_name': hero,
            'villain_code': villain_code,
            'villain_name': villain,
            'scenario_name': villain,
            'scenario_key': GameHistory._slug(villain),
            'expert': int(expert),
            'result': result,
            'rounds': 5,
            'playtime_seconds': 900,
            'seed': key,
            'remaining_hit_points': remaining_hit_points,
            'minions_in_play': minions_in_play,
            'side_schemes_in_play': side_schemes_in_play,
            'undo_count': undo_count,
            'imported_from_replay': 0,
            'source': source,
            'is_service': int(is_service),
        })

    def test_schema_v1_adds_replay_analysis_columns_without_losing_games(self):
        database_path = self.root / 'schema-v1.sqlite3'
        with closing(sqlite3.connect(database_path)) as connection, connection:
            connection.execute(
                'CREATE TABLE games (id INTEGER PRIMARY KEY, result TEXT)'
            )
            connection.execute(
                "INSERT INTO games (id, result) VALUES (1, 'unknown')"
            )
            connection.execute('PRAGMA user_version = 1')

        history = GameHistory(
            file_path=str(database_path),
            replay_folders=[],
        )
        history.enabled = True
        history.Initialize()

        with history._connect() as connection:
            # Derived rather than pinned: this test is about a v1 database
            # arriving at the current schema with its games intact, not about
            # which number that schema happens to be. Written as a literal it
            # failed on the next bump, which says nothing about migrating.
            self.assertEqual(
                connection.execute('PRAGMA user_version').fetchone()[0],
                GameHistory.SCHEMA_VERSION,
            )
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            self.assertIn('replay_analysis_status', columns)
            self.assertIn('replay_analysis_error', columns)
            self.assertIn('source', columns)
            self.assertIn('notes', columns)
            self.assertIn('hero_rating', columns)
            self.assertIn('scenario_rating', columns)
            self.assertIn('is_service', columns)
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM games').fetchone()[0],
                1,
            )

    def test_physical_game_is_in_shared_stats_and_can_be_filtered(self):
        self.record(1, result='win')
        physical = self.history.SavePhysicalGame({
            'hero_code': '60026a',
            'hero_name': 'Echo',
            'villain_code': '01113',
            'scenario_key': 'klaw',
            'scenario_name': 'Klaw',
            'expert': True,
            'result': 'loss',
            'finished_at': '2026-08-12T18:30:00+03:00',
            'rounds': 7,
            'playtime_minutes': 75,
            'deck_name': 'Echo Justice',
            'notes': 'Lost to Advance.',
        })

        self.assertTrue(physical['created'])
        dashboard = self.history.GetDashboard()
        self.assertEqual(dashboard['overview']['completed'], 2)
        self.assertEqual(dashboard['overview']['wins'], 1)
        self.assertEqual(dashboard['overview']['losses'], 1)

        physical_only = self.history.GetDashboard('physical')
        self.assertEqual(physical_only['overview']['completed'], 1)
        self.assertEqual(physical_only['overview']['losses'], 1)
        row = physical_only['recent_games'][0]
        self.assertEqual(row['source'], 'physical')
        self.assertEqual(row['hero_name'], 'Echo')
        self.assertEqual(row['rounds'], 7)
        self.assertEqual(row['playtime_seconds'], 4500)
        self.assertEqual(row['notes'], 'Lost to Advance.')

        digital_only = self.history.GetDashboard('digital')
        self.assertEqual(digital_only['overview']['completed'], 1)
        self.assertEqual(digital_only['overview']['wins'], 1)

    def test_editing_physical_game_recalculates_achievement_progress(self):
        game_ids = []
        for day, (villain, code) in enumerate((
            ('Rhino', '01094'),
            ('Klaw', '01113'),
            ('Ultron', '01135'),
        ), start=1):
            result = self.history.SavePhysicalGame({
                'hero_code': '01001a',
                'hero_name': 'Spider-Man',
                'villain_code': code,
                'scenario_key': GameHistory._slug(villain),
                'scenario_name': villain,
                'result': 'win',
                'finished_at': f'2026-08-{day:02d}T12:00:00+00:00',
            })
            game_ids.append(result['id'])

        achievement = next(
            item for item in self.history.GetDashboard()['achievements']
            if item['id'] == 'core_set_conqueror'
        )
        self.assertTrue(achievement['unlocked'])

        self.history.SavePhysicalGame({
            'id': game_ids[-1],
            'hero_code': '01001a',
            'hero_name': 'Spider-Man',
            'villain_code': '01135',
            'scenario_key': 'ultron',
            'scenario_name': 'Ultron',
            'result': 'loss',
            'finished_at': '2026-08-03T12:00:00+00:00',
        })
        achievement = next(
            item for item in self.history.GetDashboard()['achievements']
            if item['id'] == 'core_set_conqueror'
        )
        self.assertFalse(achievement['unlocked'])
        self.assertEqual(achievement['progress'], 2)

        self.history.DeletePhysicalGame(game_ids[-1])
        self.assertEqual(self.history.GetDashboard('physical')['overview']['completed'], 2)

    def test_collection_is_stored_in_same_server_database(self):
        result = self.history.SaveCollection(['core', 'gmw', 'core'])
        self.assertEqual(result['owned_products'], ['core', 'gmw'])
        self.assertEqual(
            self.history.GetDashboard()['owned_products'],
            ['core', 'gmw'],
        )

        result = self.history.SaveCollection(['gmw', 'mts'])
        self.assertEqual(result['owned_products'], ['gmw', 'mts'])
        self.assertEqual(
            self.history.GetDashboard()['owned_products'],
            ['gmw', 'mts'],
        )

    def test_physical_end_state_advances_applicable_achievements(self):
        self.history.SavePhysicalGame({
            'hero_code': '01001a',
            'hero_name': 'Spider-Man',
            'villain_code': '01094',
            'scenario_key': 'rhino',
            'scenario_name': 'Rhino',
            'result': 'win',
            'finished_at': '2026-08-12T12:00:00+00:00',
            'remaining_hit_points': 1,
            'clean_table': True,
        })

        achievements = {
            item['id']: item
            for item in self.history.GetDashboard()['achievements']
        }
        self.assertTrue(achievements['against_all_odds']['unlocked'])
        self.assertTrue(achievements['clean_table']['unlocked'])
        self.assertTrue(achievements['no_second_chances']['unlocked'])

    def test_existing_database_does_not_automatically_import_replays(self):
        replay_path = self.replay_folder / 'late-replay.json'
        replay_path.write_text(json.dumps({
            'version': '0.6.0.0',
            'metadata': {},
            'rules': ['v18_all'],
            'campaign': {'name': 'Rhino', 'villain': ['01094']},
            'players': [{'name': 'Spider-Man', 'hero': ['01001a']}],
            'inputs': [],
        }), encoding='utf-8')

        class Analyzer:
            calls = 0

            def Analyze(self, file_path):
                self.calls += 1
                raise AssertionError('Existing databases must not import replays.')

        analyzer = Analyzer()
        self.history.Initialize(analyzer)

        self.assertEqual(analyzer.calls, 0)
        with self.history._connect() as connection:
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM games').fetchone()[0],
                0,
            )

    def test_dashboard_calculates_hero_villain_and_matchup_rates(self):
        self.record(1, result='win')
        self.record(2, result='loss')
        self.record(3, villain='Klaw', villain_code='01113', result='win')
        self.record(4, villain='Ultron', villain_code='01135', result='unknown')

        dashboard = self.history.GetDashboard()

        self.assertTrue(dashboard['available'])
        self.assertEqual(dashboard['overview']['completed'], 3)
        self.assertEqual(dashboard['overview']['wins'], 2)
        self.assertEqual(dashboard['overview']['losses'], 1)
        self.assertEqual(dashboard['overview']['unknown_games'], 1)
        self.assertEqual(dashboard['overview']['win_rate'], 66.7)
        self.assertEqual(dashboard['heroes'][0]['games'], 3)
        rhino = next(row for row in dashboard['villains'] if row['villain_name'] == 'Rhino')
        self.assertEqual(rhino['games'], 2)
        self.assertEqual(rhino['win_rate'], 50.0)
        self.assertEqual(len(dashboard['matchups']), 2)

    def test_service_games_stay_in_database_but_not_user_history_or_stats(self):
        self.record(1, result='win')
        service = self.record(
            2,
            villain='Klaw',
            villain_code='01113',
            result='win',
            is_service=True,
        )

        dashboard = self.history.GetDashboard()

        self.assertEqual(dashboard['overview']['completed'], 1)
        self.assertEqual(dashboard['overview']['wins'], 1)
        self.assertEqual(dashboard['overview']['losses'], 0)
        self.assertEqual(len(dashboard['recent_games']), 1)
        self.assertEqual(dashboard['recent_games'][0]['villain_name'], 'Rhino')
        core_progress = next(
            item['progress'] for item in dashboard['achievements']
            if item['id'] == 'core_set_conqueror'
        )
        self.assertEqual(core_progress, 1)
        with self.history._connect() as connection:
            row = connection.execute(
                'SELECT is_service FROM games WHERE id = ?',
                (service['id'],),
            ).fetchone()
            self.assertEqual(row['is_service'], 1)

    def test_optional_game_ratings_are_validated_saved_and_aggregated(self):
        self.record(1, result='win')
        self.record(2, result='loss')

        first = self.history.SaveGameRatings('test:1', {
            'hero_rating': 5,
            'scenario_rating': 4,
        })
        second = self.history.SaveGameRatings('test:2', {
            'hero_rating': 3,
            'scenario_rating': 5,
        })

        self.assertEqual(first['hero_rating'], 5)
        self.assertEqual(first['scenario_rating'], 4)
        self.assertEqual(second['hero_rating'], 3)
        dashboard = self.history.GetDashboard()
        self.assertEqual(dashboard['heroes'][0]['average_rating'], 4.0)
        self.assertEqual(dashboard['heroes'][0]['rating_count'], 2)
        self.assertEqual(dashboard['villains'][0]['average_rating'], 4.5)
        self.assertEqual(dashboard['villains'][0]['rating_count'], 2)
        self.assertEqual(dashboard['recent_games'][0]['hero_rating'], 3)
        self.assertEqual(dashboard['recent_games'][0]['scenario_rating'], 5)

        with self.assertRaisesRegex(ValueError, '1 to 5'):
            self.history.SaveGameRatings('test:1', {'hero_rating': 6})
        with self.assertRaisesRegex(ValueError, 'Choose'):
            self.history.SaveGameRatings('test:1', {})

    def test_the_games_list_can_be_bounded_by_day(self):
        for key, day in ((1, '2026-08-01'), (2, '2026-08-10'), (3, '2026-08-20')):
            self.history._store_game({
                'source_key': f'day:{key}', 'finished_at': f'{day}T12:00:00+00:00',
                'hero_code': '01001a', 'hero_name': 'Spider-Man', 'villain_code': '01094',
                'villain_name': 'Rhino', 'scenario_name': 'Rhino', 'scenario_key': 'rhino',
                'result': 'win',
            })
        days = lambda dashboard: [row['finished_at'][:10] for row in dashboard['recent_games']]

        self.assertEqual(days(self.history.GetDashboard('all', '2026-08-05', '2026-08-15')), ['2026-08-10'])
        self.assertEqual(days(self.history.GetDashboard('all', '2026-08-10', '')), ['2026-08-20', '2026-08-10'])
        self.assertEqual(days(self.history.GetDashboard('all', '', '2026-08-10')), ['2026-08-10', '2026-08-01'])
        # The records above the list are not bounded: three wins, whatever the days.
        self.assertEqual(self.history.GetDashboard('all', '2026-08-05', '2026-08-15')['overview']['wins'], 3)
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            self.history.GetDashboard('all', 'yesterday', '')

    def test_rating_fields_can_be_updated_independently(self):
        self.record(1)
        self.history.SaveGameRatings('test:1', {'scenario_rating': 4})
        updated = self.history.SaveGameRatings('test:1', {'hero_rating': 2})

        self.assertEqual(updated['scenario_rating'], 4)
        self.assertEqual(updated['hero_rating'], 2)

    def completed_game(self, *, won=True):
        metadata = {'statistics_eligible': True, 'game_id': 'current-game'}
        scene = SimpleNamespace(
            GetMetadataBool=lambda key: bool(metadata.get(key, False)),
            GetMetadataStr=lambda key: str(metadata.get(key, '')),
            GetMetadataInt=lambda key: 0,
            SetMetadataStr=lambda key, value: metadata.__setitem__(key, value),
            is_puzzle=False,
            players=[SimpleNamespace(
                hero=['01001a,01001b'],
                name='Spider-Man',
                metadata={},
            )],
            campaign=SimpleNamespace(
                villain=['01094'],
                schemes=[],
                name='Rhino',
                expert=False,
                campaign_id='',
            ),
            rules=['v18_all'],
            version='0.6.1.0',
            seed=123,
            playtime=0,
            path='',
        )
        world = SimpleNamespace(
            is_game_over=True,
            game_over=SimpleNamespace(
                is_game_exit_or_undo=False,
                players_won=won,
                reason='Players Won',
            ),
            round_id=4,
            object_manager=SimpleNamespace(card_dict={}),
        )
        game = SimpleNamespace(
            scene=scene,
            world=world,
            session=SimpleNamespace(
                scene=scene,
                statistics=SimpleNamespace(dic={}),
                start_time=0,
                undo_count=0,
            ),
            controller_manager=SimpleNamespace(
                replay=SimpleNamespace(is_replay=False),
            ),
        )

        return game

    def test_current_completed_game_is_recorded_before_its_rating(self):
        game = self.completed_game()

        saved = self.history.SaveCurrentGameRatings(game, {'scenario_rating': 5})

        self.assertTrue(saved['saved'])
        self.assertEqual(saved['scenario_rating'], 5)
        self.assertEqual(self.history.GetDashboard()['overview']['wins'], 1)

    def test_the_finished_game_can_be_read_back_as_a_history_row(self):
        row = self.history.CurrentGameRecord(self.completed_game(won=False))

        self.assertEqual(row['hero_name'], 'Spider-Man (Peter Parker)')
        self.assertEqual(row['villain_name'], 'Rhino')
        self.assertEqual(row['result'], 'loss')
        self.assertEqual(row['rounds'], 4)
        self.assertIn('finished_at', row)
        # Recorded by the read, and only once.
        self.history.CurrentGameRecord(self.completed_game(won=False))
        self.assertEqual(self.history.GetDashboard()['overview']['losses'], 1)

    def test_a_replay_is_not_a_game_to_send(self):
        game = self.completed_game()
        game.controller_manager.replay.is_replay = True
        with self.assertRaisesRegex(ValueError, 'Replay'):
            self.history.CurrentGameRecord(game)


    def test_game_and_card_statistics_are_inserted_only_once(self):
        record = {
            'source_key': 'game:stable-id',
            'finished_at': '2026-08-10T12:00:00+00:00',
            'hero_code': '01001a',
            'hero_name': 'Spider-Man',
            'villain_code': '01094',
            'villain_name': 'Rhino',
            'scenario_name': 'Rhino',
            'scenario_key': 'rhino',
            'expert': 0,
            'result': 'win',
            'imported_from_replay': 0,
        }
        card_statistics = [{
            'card_id': '01003',
            'card_name': 'Backflip',
            'damage_dealt': 0,
            'damage_taken': 0,
            'thwarted_threat': 0,
            'entered_play': 2,
        }]

        first = self.history._store_game(record, card_statistics)
        second = self.history._store_game(record, card_statistics)

        self.assertTrue(first['inserted'])
        self.assertFalse(second['inserted'])
        with self.history._connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM games').fetchone()[0], 1)
            row = connection.execute(
                'SELECT card_id, entered_play FROM game_card_statistics'
            ).fetchone()
            self.assertEqual(tuple(row), ('01003', 2))

    def test_legacy_replay_imports_metadata_as_unknown_and_deduplicates(self):
        replay_path = self.replay_folder / 'legacy.json'
        replay_path.write_text(json.dumps({
            'version': '0.5.9.201',
            'metadata': {
                'seed': 12345,
                'time': '2026-08-08 21-04',
                'playtime': '958.3',
            },
            'rules': ['v16_all'],
            'campaign': {
                'name': 'Klaw',
                'villain': ['01113'],
                'expert': True,
            },
            'players': [{
                'name': 'Spider-Man',
                'hero': ['01001a,01001b'],
            }],
            'inputs': [],
        }), encoding='utf-8')

        self.assertEqual(self.history.ImportReplays(), 1)
        self.assertEqual(self.history.ImportReplays(), 0)
        dashboard = self.history.GetDashboard()

        self.assertEqual(dashboard['overview']['completed'], 0)
        self.assertEqual(dashboard['overview']['unknown_games'], 1)
        imported = dashboard['recent_games'][0]
        # Peter Parker's card is one of two named Spider-Man, so the row says which.
        self.assertEqual(imported['hero_name'], 'Spider-Man (Peter Parker)')
        self.assertEqual(imported['villain_name'], 'Klaw')
        self.assertEqual(imported['expert'], 1)
        self.assertEqual(imported['result'], 'unknown')
        with self.history._connect() as connection:
            row = connection.execute(
                'SELECT replay_analysis_status, replay_analysis_error FROM games'
            ).fetchone()
            self.assertEqual(row['replay_analysis_status'], 'unsupported')
            self.assertIn('Rules Reference 1.8-only', row['replay_analysis_error'])

    def test_new_replay_result_is_imported_without_replaying_game(self):
        replay_path = self.replay_folder / 'new.json'
        replay_path.write_text(json.dumps({
            'version': '0.6.0.0',
            'metadata': {
                'game_id': 'stable-game-id',
                'game_result': 'loss',
                'game_over_reason': 'The Main Scheme was Completed',
                'rounds': 4,
                'seed': 9876,
                'time': '2026-08-10T12:00:00+00:00',
                'statistics_eligible': True,
            },
            'rules': ['v18_all'],
            'campaign': {
                'name': 'Ultron',
                'villain': ['01135'],
                'expert': False,
            },
            'players': [{
                'name': 'Echo',
                'hero': ['60026a,60026b'],
                'deck_name': 'Echo Justice',
                'metadata': {'source': 'starter'},
            }],
            'inputs': [],
        }), encoding='utf-8')

        self.assertEqual(self.history.ImportReplays(), 1)
        dashboard = self.history.GetDashboard()

        self.assertEqual(dashboard['overview']['completed'], 1)
        self.assertEqual(dashboard['overview']['losses'], 1)
        self.assertEqual(dashboard['recent_games'][0]['rounds'], 4)
        with self.history._connect() as connection:
            row = connection.execute(
                'SELECT source_key, deck_name, rules_version FROM games'
            ).fetchone()
            self.assertEqual(tuple(row), ('game:stable-game-id', 'Echo Justice', 'v18'))

    def test_unknown_v18_replay_is_analyzed_and_existing_row_is_updated(self):
        replay_path = self.replay_folder / 'analyze.json'
        replay_path.write_text(json.dumps({
            'version': '0.6.0.0',
            'metadata': {
                'seed': 2468,
                'time': '2026-08-10T12:00:00+00:00',
            },
            'rules': ['v18_all'],
            'campaign': {
                'name': 'Rhino',
                'villain': ['01094'],
                'expert': False,
            },
            'players': [{
                'name': 'Spider-Man',
                'hero': ['01001a,01001b'],
            }],
            'inputs': [],
        }), encoding='utf-8')

        # The metadata-only pass represents a database created before outcome
        # replay analysis was available.
        self.assertEqual(self.history.ImportReplays(), 1)
        self.assertEqual(
            self.history.GetDashboard()['overview']['unknown_games'],
            1,
        )

        class Analyzer:
            calls = 0

            def Analyze(self, file_path):
                self.calls += 1
                self.last_path = file_path
                return ReplayOutcome(
                    result='win',
                    game_over_reason='The Final Stage of the Villain was Defeated',
                    rounds=6,
                    remaining_hit_points=3,
                    minions_in_play=0,
                    side_schemes_in_play=1,
                )

        analyzer = Analyzer()
        self.assertEqual(self.history.ImportReplays(analyzer), 0)
        self.assertEqual(analyzer.calls, 1)

        dashboard = self.history.GetDashboard()
        self.assertEqual(dashboard['overview']['wins'], 1)
        self.assertEqual(dashboard['overview']['unknown_games'], 0)
        with self.history._connect() as connection:
            row = connection.execute(
                'SELECT result, rounds, remaining_hit_points, '
                'side_schemes_in_play, replay_analysis_status, '
                'replay_analysis_error FROM games'
            ).fetchone()
            self.assertEqual(
                tuple(row),
                ('win', 6, 3, 1, 'resolved', ''),
            )

        # A known result is never replayed again on the next startup/import.
        self.assertEqual(self.history.ImportReplays(analyzer), 0)
        self.assertEqual(analyzer.calls, 1)

    def test_non_solo_puzzle_and_ineligible_replays_are_not_imported(self):
        base = {
            'version': '0.6.0.0',
            'metadata': {},
            'rules': ['v18_all'],
            'campaign': {'name': 'Rhino', 'villain': ['01094']},
            'players': [{'name': 'Spider-Man', 'hero': ['01001a']}],
            'inputs': [],
        }
        # Five, not two: the recorder takes up to the four seats the engine
        # has, so a replay is only refused for having more than the engine
        # could have produced.
        multiplayer = {**base, 'players': base['players'] * 5}
        puzzle = {**base, 'puzzle': ['Puzzle.CreateHandCards()']}
        ineligible = {**base, 'metadata': {'statistics_eligible': False}}
        mcp_game = {**base, 'metadata': {'statistics_excluded': True}}
        for index, replay in enumerate((multiplayer, puzzle, ineligible, mcp_game)):
            (self.replay_folder / f'skip-{index}.json').write_text(
                json.dumps(replay),
                encoding='utf-8',
            )

        self.assertEqual(self.history.ImportReplays(), 0)
        self.assertEqual(self.history.GetDashboard()['overview']['unknown_games'], 0)

    def test_a_two_handed_replay_is_imported_for_both_heroes(self):
        """The counterpart to the rule above: two is one person's game."""
        replay = {
            'version': '0.7.7.0',
            'metadata': {'game_result': 'win', 'game_id': 'two-handed'},
            'rules': ['v18_all'],
            'campaign': {'name': 'Rhino', 'villain': ['01094']},
            'players': [
                {'name': 'Spider-Man', 'hero': ['01001a']},
                {'name': 'Cable', 'hero': ['40001a']},
            ],
            'inputs': [],
        }
        (self.replay_folder / 'two-handed.json').write_text(
            json.dumps(replay), encoding='utf-8')

        self.assertEqual(self.history.ImportReplays(), 1)
        heroes = self.history.GetDashboard()['heroes']
        self.assertEqual(
            {row['hero_code'] for row in heroes}, {'01001a', '40001a'})
        # One game, played by two heroes, not two games.
        self.assertEqual(self.history.GetDashboard()['overview']['completed'], 1)

    def test_game_over_metadata_makes_future_replay_import_exact(self):
        scene = Scene(metadata={
            'seed': 4321,
            'game_id': 'first-attempt',
            'time': '2026-08-10 12-00',
            'playtime': '300.0',
            'path': './replays/first-attempt.json',
        }, rules=['v18_all'])
        player = SimpleNamespace(
            GetIdentity=lambda: SimpleNamespace(health=1),
            GetEngagedMinions=lambda: [],
        )
        game = SimpleNamespace(
            scene=scene,
            world=SimpleNamespace(
                const_players=[player],
                round_id=7,
                area_schemes_side=SimpleNamespace(GetSize=lambda: 0),
            ),
            session=SimpleNamespace(scene=scene, cheat=False, undo_count=2),
            controller_manager=SimpleNamespace(
                replay=SimpleNamespace(is_replay=False, history_inputs=[]),
            ),
        )

        GameHistory.CaptureOutcomeMetadata(
            game,
            True,
            'The Final Stage of the Villain was Defeated',
        )

        self.assertEqual(scene.GetMetadataStr('game_result'), 'win')
        self.assertEqual(scene.GetMetadataInt('rounds'), 7)
        self.assertEqual(scene.GetMetadataInt('remaining_hit_points'), 1)
        self.assertEqual(scene.GetMetadataInt('undo_count'), 2)
        self.assertTrue(scene.GetMetadataBool('statistics_eligible'))

        game.statistics_excluded = True
        GameHistory.CaptureOutcomeMetadata(
            game,
            True,
            'The Final Stage of the Villain was Defeated',
        )
        self.assertFalse(scene.GetMetadataBool('statistics_eligible'))
        self.assertTrue(scene.GetMetadataBool('statistics_excluded'))

        GameHistory.ResetSceneOutcome(scene)
        self.assertEqual(scene.GetMetadataStr('game_id'), '')
        self.assertEqual(scene.GetMetadataStr('game_result'), '')
        self.assertEqual(scene.GetMetadataInt('rounds'), 0)
        self.assertEqual(scene.GetMetadataFloat('playtime'), 0)
        self.assertEqual(scene.GetMetadataStr('path'), '')
        self.assertFalse(scene.GetMetadataBool('statistics_eligible'))

    def test_all_initial_achievements_can_be_earned_from_history(self):
        key = 10
        for villain, code in (
            ('Rhino', '01094'),
            ('Klaw', '01113'),
            ('Ultron', '01135'),
        ):
            self.record(key, villain=villain, villain_code=code)
            key += 1

        # These are consecutive Expert wins against different villains and
        # simultaneously satisfy The Hardest Road.
        for villain, code in (
            ('Ronan the Accuser', '16103'),
            ('Venom Goblin', '39001'),
            ('Magneto', '32159'),
        ):
            self.record(key, villain=villain, villain_code=code, expert=True)
            key += 1

        for villain, code in (
            ('Rhino', '01094'),
            ('Klaw', '01113'),
            ('Ultron', '01135'),
        ):
            self.record(key, villain=villain, villain_code=code, expert=True)
            key += 1

        # Bring one hero to ten distinct defeated villains.
        for index in range(10):
            self.record(
                key,
                hero='Echo',
                hero_code='60026a',
                villain=f'Test Villain {index}',
                villain_code=f'9{index:04d}',
            )
            key += 1

        self.record(
            key,
            hero='Wonder Man',
            hero_code='58001a',
            villain='Rhino',
            remaining_hit_points=1,
            minions_in_play=0,
            side_schemes_in_play=0,
            undo_count=0,
        )

        achievements = self.history.GetDashboard()['achievements']

        self.assertEqual(len(achievements), len(ACHIEVEMENTS))
        self.assertTrue(all(item['unlocked'] for item in achievements))
        with self.history._connect() as connection:
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM achievements').fetchone()[0],
                len(ACHIEVEMENTS),
            )



class HeroicDifficultyTests(unittest.TestCase):
    """The Heroic ladder, and the migration that made room for it.

    One square on the coverage grid makes one claim -- the hardest difficulty
    that pairing has actually been beaten at -- so the ordering matters more
    than the counts do.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / 'statistics.sqlite3'
        self.history = GameHistory(file_path=str(self.path), replay_folders=[])
        self.history.enabled = True
        self.history.Initialize()

    def tearDown(self):
        self.history.Close()
        try:
            self.temp_dir.cleanup()
        except OSError:
            # Windows will not unlink the database while it is still mapped.
            pass

    def record(self, scenario, expert, heroic, result):
        with self.history._lock, self.history._connect() as connection:
            cursor = connection.execute(
                'INSERT INTO games (source_key, finished_at, imported_at,'
                ' hero_code, scenario_key, expert, heroic, result)'
                ' VALUES (?,?,?,?,?,?,?,?)',
                (f'{scenario}:{expert}:{heroic}:{result}', '2026-01-01',
                 '2026-01-01', 'HERO', scenario, expert, heroic, result))
            # Who played it. Since two-handed games, that is a row of its own
            # rather than a column on the game, and a game without one is not
            # a game anybody played.
            connection.execute(
                'INSERT INTO game_players (game_id, seat, hero_code, hero_name)'
                " VALUES (?, 0, 'HERO', 'Hero')",
                (cursor.lastrowid,))

    def beaten(self, scenario):
        for row in self.history.GetMatchupCounts('all'):
            if row['scenario_key'] == scenario:
                return row['best_beaten']
        return None

    def test_the_ladder_runs_standard_expert_then_heroic_by_level(self):
        self.record('a', 0, 0, 'win')
        self.record('b', 1, 0, 'win')
        self.record('c', 0, 1, 'win')
        self.record('d', 0, 2, 'win')
        self.assertEqual(
            [self.beaten('a'), self.beaten('b'), self.beaten('c'), self.beaten('d')],
            [1, 2, 3, 4],
        )

    def test_heroic_outranks_expert(self):
        # The rule as asked for: Heroic is harder than Expert, so a Heroic 1
        # clear beats an Expert one even without Expert also being on.
        self.record('x', 1, 0, 'win')
        self.record('y', 0, 1, 'win')
        self.assertGreater(self.beaten('y'), self.beaten('x'))

    def test_expert_and_heroic_together_score_by_the_heroic_level(self):
        # Not stacked: Expert plus Heroic 1 is a Heroic 1 clear, not a Heroic 2
        # one, because the level is what sets the extra encounter cards.
        self.record('x', 1, 1, 'win')
        self.record('y', 0, 1, 'win')
        self.assertEqual(self.beaten('x'), self.beaten('y'))

    def test_a_loss_at_heroic_is_not_a_clear(self):
        self.record('a', 0, 3, 'loss')
        self.assertEqual(self.beaten('a'), 0)

    def test_the_best_clear_wins_however_the_games_are_ordered(self):
        self.record('a', 0, 2, 'win')
        self.record('a', 0, 0, 'win')
        self.record('a', 1, 0, 'win')
        self.assertEqual(self.beaten('a'), 4)

    def test_the_level_is_read_from_the_scene_rules(self):
        self.assertEqual(GameHistory.HeroicLevel(['v18_all', 'mode_heroic_3']), 3)
        self.assertEqual(GameHistory.HeroicLevel(['v18_all']), 0)
        self.assertEqual(GameHistory.HeroicLevel([]), 0)
        self.assertEqual(GameHistory.HeroicLevel(None), 0)
        # A hand-edited replay should not stop a game being recorded.
        self.assertEqual(GameHistory.HeroicLevel(['mode_heroic_x']), 0)

    def test_a_physical_game_keeps_its_heroic_level_through_an_edit(self):
        """The level has to come back out, or editing silently clears it.

        The form is repopulated from the recent-games list, so a level the
        query does not select reads as undefined and saves back as 0 -- the
        game would quietly drop to Standard the next time it was touched.
        """
        self.history.SavePhysicalGame({
            'hero_code': 'HERO', 'hero_name': 'Spider-Man',
            'scenario_key': 'rhino', 'villain_code': 'V',
            'scenario_name': 'Rhino', 'expert': True, 'heroic': 3,
            'result': 'win', 'finished_at': '2026-09-07T12:00:00Z',
        })
        row = self.history.GetDashboard('all')['recent_games'][0]
        self.assertEqual(row['heroic'], 3)
        self.assertEqual(row['expert'], 1)
        self.assertEqual(self.history.GetMatchupCounts('all')[0]['best_beaten'], 5)

    def test_an_older_database_gains_the_column_and_keeps_its_games(self):
        """The migration, which runs against a database holding real games."""
        self.history.Close()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('ALTER TABLE games DROP COLUMN heroic')
            connection.execute('PRAGMA user_version = 5')
            connection.execute(
                'INSERT INTO games (source_key, finished_at, imported_at,'
                " hero_code, scenario_key, expert, result)"
                " VALUES ('old','2026-01-01','2026-01-01','HERO','scen',1,'win')")

        migrated = GameHistory(file_path=str(self.path), replay_folders=[])
        migrated.enabled = True
        migrated.Initialize()
        try:
            with closing(sqlite3.connect(self.path)) as connection, connection:
                version = connection.execute('PRAGMA user_version').fetchone()[0]
                columns = {
                    row[1] for row in connection.execute('PRAGMA table_info(games)')
                }
                kept = connection.execute('SELECT COUNT(*) FROM games').fetchone()[0]
            # Against SCHEMA_VERSION rather than the number it was when this
            # was written: what the test means is "migrated all the way up",
            # and a literal here fails on every future bump for no reason,
            # exactly as line 101 already does it.
            self.assertEqual(version, GameHistory.SCHEMA_VERSION)
            self.assertIn('heroic', columns)
            self.assertEqual(kept, 1, 'the migration must not lose games')
            # The pre-existing Expert win still reads as one.
            self.assertEqual(
                migrated.GetMatchupCounts('all')[0]['best_beaten'], 2)
        finally:
            migrated.Close()
        self.history = migrated


if __name__ == '__main__':
    unittest.main()
