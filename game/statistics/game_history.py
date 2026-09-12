from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import threading
from typing import Any, Dict, Iterator, List, Sequence, TYPE_CHECKING
import uuid

from core.lib import Time
from engine.config import ConfigVariables
from engine.file import FileManager
from engine.log import Log
from game.statistics.achievements import AchievementEvaluator

if TYPE_CHECKING:
    from game.statistics.replay_outcome_analyzer import ReplayOutcomeAnalyzer


CATEGORY_NAME = 'STATISTICS'

GAME_HISTORY = ConfigVariables.Bool('game_history', True)
GAME_HISTORY_FILE = ConfigVariables.File(
    'game_history_file',
    './statistics.sqlite3',
)
REPLAY_FOLDERS = ConfigVariables.Folders('replay_folders', ['./replays/'])


class GameHistory:
    SCHEMA_VERSION = 8
    KNOWN_RESULTS = ('win', 'loss', 'unknown', 'abandoned')
    # Marvel Champions is a one to four player game, and the engine seats four.
    # Here so that the recorder's bound is the game's rather than one of its own.
    MAX_PLAYERS = 4
    KNOWN_SOURCES = ('digital', 'physical', 'replay_import')

    def __init__(self, file_path: str|None=None, replay_folders: List[str]|None=None) -> None:
        self.file_path = file_path or GAME_HISTORY_FILE.value
        self.replay_folders = replay_folders if replay_folders is not None else REPLAY_FOLDERS.value
        self.enabled = GAME_HISTORY.value
        self.available = False
        self._lock = threading.RLock()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """A connection for one operation, committed and then closed.

        `with sqlite3.connect(...) as connection` does not close anything --
        it commits on success and rolls back on an exception, and leaves the
        connection open. Every call site here is a `with`, so for as long as
        this returned a bare connection each operation leaked one: a container
        left running accumulated open handles on the database, and on Windows
        nothing could delete the file afterwards, which is what made eighteen
        tests fail in teardown on that platform and nowhere else.

        Wrapping the transaction in a try/finally keeps the commit-or-rollback
        the call sites already rely on and adds the close they assumed.
        """
        connection = sqlite3.connect(self.file_path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA busy_timeout = 20000')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def Initialize(
        self,
        outcome_analyzer: 'ReplayOutcomeAnalyzer|None'=None,
    ) -> None:
        if not self.enabled:
            return
        try:
            database_existed = FileManager.IsFile(self.file_path)
            FileManager.MakeDir(FileManager.GetDirName(self.file_path))
            with self._lock, self._connect() as connection:
                connection.execute('PRAGMA journal_mode = WAL')
                connection.execute('PRAGMA synchronous = NORMAL')
                self._migrate(connection)
            self.available = True
            imported = (
                0
                if database_existed
                else self.ImportReplays(outcome_analyzer)
            )
            Log.Info(
                CATEGORY_NAME,
                # Absolute, deliberately. A relative './statistics.sqlite3'
                # reads the same whether or not the volume it is supposed to
                # live on is mounted, and a missing mount looks exactly like
                # data loss on the next rebuild.
                f'Game history ready: {os.path.abspath(self.file_path)} '
                f'({imported} replay(s) imported)',
            )
        except Exception as exc:
            self.available = False
            Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)

    def Close(self) -> None:
        # Nothing to close: _connect opens a connection per operation and
        # closes it again on the way out. Kept because callers say so at
        # shutdown, and because a history that later holds something open
        # should have somewhere to release it.
        pass

    def _migrate(self, connection: sqlite3.Connection) -> None:
        version = int(connection.execute('PRAGMA user_version').fetchone()[0])
        if version > self.SCHEMA_VERSION:
            raise RuntimeError(
                f'Game history schema {version} is newer than supported '
                f'{self.SCHEMA_VERSION}.'
            )
        if version == 0:
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_key TEXT NOT NULL UNIQUE,
                    finished_at TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    engine_version TEXT NOT NULL DEFAULT '',
                    rules_version TEXT NOT NULL DEFAULT '',
                    hero_code TEXT NOT NULL DEFAULT '',
                    hero_name TEXT NOT NULL DEFAULT '',
                    villain_code TEXT NOT NULL DEFAULT '',
                    villain_name TEXT NOT NULL DEFAULT '',
                    scenario_name TEXT NOT NULL DEFAULT '',
                    scenario_key TEXT NOT NULL DEFAULT '',
                    expert INTEGER NOT NULL DEFAULT 0 CHECK (expert IN (0, 1)),
                    -- 0 when Heroic was off, otherwise the level played. A
                    -- level rather than a flag because Heroic stacks: each
                    -- one deals another encounter card per player.
                    heroic INTEGER NOT NULL DEFAULT 0 CHECK (heroic >= 0),
                    result TEXT NOT NULL DEFAULT 'unknown'
                        CHECK (result IN ('win', 'loss', 'unknown', 'abandoned')),
                    game_over_reason TEXT NOT NULL DEFAULT '',
                    rounds INTEGER,
                    playtime_seconds REAL,
                    seed INTEGER,
                    campaign_id TEXT NOT NULL DEFAULT '',
                    game_mode TEXT NOT NULL DEFAULT 'quick',
                    deck_name TEXT NOT NULL DEFAULT '',
                    deck_source TEXT NOT NULL DEFAULT '',
                    remaining_hit_points INTEGER,
                    minions_in_play INTEGER,
                    side_schemes_in_play INTEGER,
                    undo_count INTEGER,
                    replay_file TEXT NOT NULL DEFAULT '',
                    imported_from_replay INTEGER NOT NULL DEFAULT 0
                        CHECK (imported_from_replay IN (0, 1)),
                    replay_analysis_status TEXT NOT NULL DEFAULT '',
                    replay_analysis_error TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'digital'
                        CHECK (source IN ('digital', 'physical', 'replay_import')),
                    notes TEXT NOT NULL DEFAULT '',
                    hero_rating INTEGER CHECK (hero_rating BETWEEN 1 AND 5),
                    scenario_rating INTEGER CHECK (scenario_rating BETWEEN 1 AND 5),
                    is_service INTEGER NOT NULL DEFAULT 0
                        CHECK (is_service IN (0, 1))
                );

                CREATE INDEX IF NOT EXISTS games_result_index
                    ON games(result, id);
                CREATE INDEX IF NOT EXISTS games_hero_index
                    ON games(hero_code, result);
                CREATE INDEX IF NOT EXISTS games_scenario_index
                    ON games(scenario_key, result);
                CREATE INDEX IF NOT EXISTS games_matchup_index
                    ON games(hero_code, scenario_key, expert, result);
                CREATE INDEX IF NOT EXISTS games_source_index
                    ON games(source, result, id);

                CREATE TABLE IF NOT EXISTS game_card_statistics (
                    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    card_id TEXT NOT NULL,
                    card_name TEXT NOT NULL DEFAULT '',
                    damage_dealt INTEGER NOT NULL DEFAULT 0,
                    damage_taken INTEGER NOT NULL DEFAULT 0,
                    thwarted_threat INTEGER NOT NULL DEFAULT 0,
                    entered_play INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (game_id, card_id)
                );

                CREATE TABLE IF NOT EXISTS achievements (
                    achievement_id TEXT PRIMARY KEY,
                    unlocked_at TEXT NOT NULL,
                    unlocked_game_id INTEGER REFERENCES games(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS collection_products (
                    product_key TEXT PRIMARY KEY,
                    owned_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Starred decks. Here rather than in the browser because one
                -- container is played from several of them, and a star set on
                -- the laptop meant nothing on the phone.
                CREATE TABLE IF NOT EXISTS favorite_decks (
                    deck_id TEXT PRIMARY KEY,
                    favorited_at TEXT NOT NULL
                );

                -- Who played a game. One row for a solo game, two for a
                -- two-handed one, so a win counts for both heroes without the
                -- game itself being counted twice: games answers "how did this
                -- game go", this answers "who was in it".
                CREATE TABLE IF NOT EXISTS game_players (
                    game_id INTEGER NOT NULL
                        REFERENCES games(id) ON DELETE CASCADE,
                    seat INTEGER NOT NULL,
                    hero_code TEXT NOT NULL DEFAULT '',
                    hero_name TEXT NOT NULL DEFAULT '',
                    deck_name TEXT NOT NULL DEFAULT '',
                    deck_source TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (game_id, seat)
                );

                CREATE INDEX IF NOT EXISTS game_players_hero_index
                    ON game_players(hero_code);
                '''
            )
            connection.execute(f'PRAGMA user_version = {self.SCHEMA_VERSION}')
            version = self.SCHEMA_VERSION

        if version < 2:
            connection.execute(
                "ALTER TABLE games ADD COLUMN replay_analysis_status "
                "TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "ALTER TABLE games ADD COLUMN replay_analysis_error "
                "TEXT NOT NULL DEFAULT ''"
            )
            connection.execute('PRAGMA user_version = 2')
            version = 2

        if version < 3:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'source' not in columns:
                connection.execute(
                    "ALTER TABLE games ADD COLUMN source TEXT NOT NULL "
                    "DEFAULT 'digital' CHECK (source IN "
                    "('digital', 'physical', 'replay_import'))"
                )
            if 'notes' not in columns:
                connection.execute(
                    "ALTER TABLE games ADD COLUMN notes TEXT NOT NULL DEFAULT ''"
                )
            if 'imported_from_replay' in columns:
                connection.execute(
                    "UPDATE games SET source = 'replay_import' "
                    'WHERE imported_from_replay = 1'
                )
            connection.executescript(
                '''
                CREATE INDEX IF NOT EXISTS games_source_index
                    ON games(source, result, id);
                CREATE TABLE IF NOT EXISTS collection_products (
                    product_key TEXT PRIMARY KEY,
                    owned_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                '''
            )
            connection.execute('PRAGMA user_version = 3')
            version = 3

        if version < 4:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'hero_rating' not in columns:
                connection.execute(
                    'ALTER TABLE games ADD COLUMN hero_rating INTEGER '
                    'CHECK (hero_rating BETWEEN 1 AND 5)'
                )
            if 'scenario_rating' not in columns:
                connection.execute(
                    'ALTER TABLE games ADD COLUMN scenario_rating INTEGER '
                    'CHECK (scenario_rating BETWEEN 1 AND 5)'
                )
            connection.execute('PRAGMA user_version = 4')
            version = 4

        if version < 5:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'is_service' not in columns:
                connection.execute(
                    'ALTER TABLE games ADD COLUMN is_service INTEGER '
                    'NOT NULL DEFAULT 0 CHECK (is_service IN (0, 1))'
                )
            connection.execute('PRAGMA user_version = 5')
            version = 5

        if version < 6:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'heroic' not in columns:
                # Existing rows take 0, which is honest rather than merely
                # convenient: nothing before this column could record a Heroic
                # level, so every game already here was played without one or
                # played at a level nothing preserved.
                connection.execute(
                    'ALTER TABLE games ADD COLUMN heroic INTEGER '
                    'NOT NULL DEFAULT 0 CHECK (heroic >= 0)'
                )
            connection.execute('PRAGMA user_version = 6')
            version = 6

        if version < 7:
            connection.execute(
                '''
                CREATE TABLE IF NOT EXISTS favorite_decks (
                    deck_id TEXT PRIMARY KEY,
                    favorited_at TEXT NOT NULL
                )
                '''
            )
            connection.execute('PRAGMA user_version = 7')
            version = 7

        if version < 8:
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS game_players (
                    game_id INTEGER NOT NULL
                        REFERENCES games(id) ON DELETE CASCADE,
                    seat INTEGER NOT NULL,
                    hero_code TEXT NOT NULL DEFAULT '',
                    hero_name TEXT NOT NULL DEFAULT '',
                    deck_name TEXT NOT NULL DEFAULT '',
                    deck_source TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (game_id, seat)
                );

                CREATE INDEX IF NOT EXISTS game_players_hero_index
                    ON game_players(hero_code);
                '''
            )
            # Every game recorded so far had exactly one hero, in seat 0.
            # Backfilled rather than left to the readers, so there is one
            # answer to "who played this" and not two.
            #
            # Only from the columns the table actually has: a database that
            # arrived here from an early schema may never have gained them,
            # and a migration that assumes its own history is how an upgrade
            # fails on the one database nobody can replace.
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            carried = [
                name if name in columns else "''"
                for name in ('hero_code', 'hero_name', 'deck_name', 'deck_source')
            ]
            connection.execute(
                'INSERT OR IGNORE INTO game_players '
                '(game_id, seat, hero_code, hero_name, deck_name, deck_source) '
                f'SELECT id, 0, {", ".join(carried)} FROM games'
            )
            connection.execute('PRAGMA user_version = 8')

    @staticmethod
    def HeroicLevel(rules: Any) -> int:
        """The Heroic level a set of scene rules describes, or 0 for none.

        Taken from the rules rather than from the running world, because the
        rules are what a replay preserves -- reading the world would record
        the level for a live game and lose it on every import.
        """
        try:
            for rule in rules or []:
                text = str(rule)
                if text.startswith('mode_heroic_'):
                    level = int(text[len('mode_heroic_'):])
                    return level if level > 0 else 0
        except (TypeError, ValueError):
            # A hand-edited replay should not stop the game being recorded.
            return 0
        return 0

    @staticmethod
    def NewGameId() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _slug(value: str) -> str:
        value = value.strip().lower().replace('&', ' and ')
        return re.sub(r'[^a-z0-9]+', '_', value).strip('_')

    @staticmethod
    def _first_card_id(cards: Any) -> str:
        if not isinstance(cards, list) or not cards:
            return ''
        return str(cards[0]).split(',')[0].strip().lower()

    @staticmethod
    def _safe_int(value: Any) -> int|None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float|None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _normalize_finished_at(cls, value: Any, file_path: str) -> str:
        text = str(value or '').strip()
        if text:
            try:
                return datetime.fromisoformat(text).isoformat()
            except ValueError:
                try:
                    local_time = datetime.strptime(text, '%Y-%m-%d %H-%M')
                    return local_time.astimezone().isoformat()
                except ValueError:
                    pass
        return datetime.fromtimestamp(
            os.path.getmtime(file_path),
            timezone.utc,
        ).isoformat()

    @classmethod
    def EnsureSceneGameId(cls, scene: Any) -> str:
        game_id = scene.GetMetadataStr('game_id')
        if not game_id:
            game_id = cls.NewGameId()
            scene.SetMetadataStr('game_id', game_id)
        return game_id

    @staticmethod
    def ResetSceneOutcome(scene: Any) -> None:
        for key in (
            'game_id',
            'game_result',
            'game_over_reason',
            'statistics_eligible',
            'rounds',
            'remaining_hit_points',
            'minions_in_play',
            'side_schemes_in_play',
            'undo_count',
            'time',
            'playtime',
            'path',
        ):
            scene.metadata.pop(key, None)

    @staticmethod
    def CaptureOutcomeMetadata(game: Any, players_won: bool, reason: str) -> None:
        scene = game.scene
        world = game.world
        if not world:
            return
        if getattr(game, 'statistics_excluded', False):
            scene.SetMetadataBool('statistics_excluded', True)
        scene.SetMetadataStr('game_result', 'win' if players_won else 'loss')
        scene.SetMetadataStr('game_over_reason', reason)
        scene.SetMetadataBool(
            'statistics_eligible',
            GameHistory.IsEligibleLiveGame(game),
        )
        scene.SetMetadataInt('rounds', world.round_id)
        scene.SetMetadataInt('undo_count', game.session.undo_count)
        if len(world.const_players) == 1:
            player = world.const_players[0]
            scene.SetMetadataInt(
                'remaining_hit_points',
                max(0, int(player.GetIdentity().health)),
            )
            scene.SetMetadataInt('minions_in_play', len(player.GetEngagedMinions()))
            scene.SetMetadataInt(
                'side_schemes_in_play',
                world.area_schemes_side.GetSize(),
            )

    @staticmethod
    def IsEligibleLiveGame(game: Any) -> bool:
        if not game.world or not game.session.scene:
            return False
        if (
            getattr(game, 'statistics_excluded', False)
            or game.scene.GetMetadataBool('statistics_excluded')
        ):
            return False
        # One to four, which is what the game itself supports -- not a limit
        # of this recorder, which has a row per seat and would take any number.
        # Quick Game only sets up one hero or two, but a game reaching here
        # with three was still played, and refusing to record it would be the
        # same silent loss this table was added to stop.
        if not 1 <= len(game.world.const_players) <= GameHistory.MAX_PLAYERS:
            return False
        if game.scene.is_puzzle or game.controller_manager.replay.is_replay:
            return False
        if game.session.cheat:
            return False
        if any(
            getattr(item, 'effect', None) and item.effect.GetDebugCommand()
            for item in game.controller_manager.replay.history_inputs
        ):
            return False
        from game.test import Test
        return not Test.IsInTesting()

    def _should_record_live_game(self, game: Any) -> bool:
        return self.available and self.IsEligibleLiveGame(game)

    def _live_record(self, game: Any) -> Dict[str, Any]:
        scene = game.scene
        world = game.world
        assert world
        player = scene.players[0]
        campaign = scene.campaign
        result = 'win' if world.game_over.players_won else 'loss'
        game_id = self.EnsureSceneGameId(scene)
        villain_code = self._first_card_id(campaign.villain or campaign.schemes)
        scenario_name = campaign.name or villain_code
        metadata = getattr(player, 'metadata', {}) or {}
        playtime = max(0.0, Time.GetTime() - game.session.start_time + scene.playtime)
        players = [
            {
                'seat': seat,
                'hero_code': self._first_card_id(seated.hero),
                'hero_name': seated.name,
                'deck_name': getattr(seated, 'deck_name', '') or seated.name,
                'deck_source': str(
                    (getattr(seated, 'metadata', {}) or {}).get(
                        'source',
                        (getattr(seated, 'metadata', {}) or {}).get('url', 'starter'),
                    )
                ),
            }
            for seat, seated in enumerate(scene.players)
        ]
        return {
            'players': players,
            'source_key': f'game:{game_id}',
            'finished_at': self._now(),
            'engine_version': scene.version,
            'rules_version': 'v18' if 'v18_all' in scene.rules else '',
            'hero_code': self._first_card_id(player.hero),
            'hero_name': player.name,
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': self._slug(scenario_name),
            'expert': int(bool(campaign.expert)),
            'heroic': self.HeroicLevel(scene.rules),
            'result': result,
            'game_over_reason': str(world.game_over.reason or ''),
            'rounds': world.round_id,
            'playtime_seconds': playtime,
            'seed': scene.seed,
            'campaign_id': campaign.campaign_id,
            'game_mode': 'campaign' if 'mode_campaign' in scene.rules else 'quick',
            'deck_name': getattr(player, 'deck_name', '') or player.name,
            'deck_source': str(metadata.get('source', metadata.get('url', 'starter'))),
            'remaining_hit_points': scene.GetMetadataInt('remaining_hit_points'),
            'minions_in_play': scene.GetMetadataInt('minions_in_play'),
            'side_schemes_in_play': scene.GetMetadataInt('side_schemes_in_play'),
            'undo_count': game.session.undo_count,
            'replay_file': scene.path,
            'imported_from_replay': 0,
            'source': 'digital',
        }

    def _live_card_statistics(self, game: Any) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        world = game.world
        if not world:
            return []
        for object_id, values in game.session.statistics.dic.items():
            card = world.object_manager.card_dict.get(object_id)
            if not card:
                continue
            card_id = card.face.paper.card_id
            row = grouped.setdefault(card_id, {
                'card_id': card_id,
                'card_name': card.face.name,
                'damage_dealt': 0,
                'damage_taken': 0,
                'thwarted_threat': 0,
                'entered_play': 0,
            })
            for key in ('damage_dealt', 'damage_taken', 'thwarted_threat', 'entered_play'):
                row[key] += int(values.get(key, 0))
        return list(grouped.values())

    def RecordCompletedGame(self, game: Any) -> List[str]:
        if not self._should_record_live_game(game):
            return []
        record = self._live_record(game)
        return self._store_game(record, self._live_card_statistics(game))['unlocked']

    def _store_game(
        self,
        record: Dict[str, Any],
        card_statistics: List[Dict[str, Any]]|None=None,
    ) -> Dict[str, Any]:
        if not self.available:
            return {
                'inserted': False,
                'updated': False,
                'id': None,
                'unlocked': [],
            }
        columns = (
            'source_key', 'finished_at', 'imported_at', 'engine_version',
            'rules_version', 'hero_code', 'hero_name', 'villain_code',
            'villain_name', 'scenario_name', 'scenario_key', 'expert',
            'heroic', 'result',
            'game_over_reason', 'rounds', 'playtime_seconds', 'seed',
            'campaign_id', 'game_mode', 'deck_name', 'deck_source',
            'remaining_hit_points', 'minions_in_play', 'side_schemes_in_play',
            'undo_count', 'replay_file', 'imported_from_replay',
            'replay_analysis_status', 'replay_analysis_error',
            'source', 'notes', 'hero_rating', 'scenario_rating',
            'is_service',
        )
        values = {
            'source_key': '',
            'finished_at': self._now(),
            'imported_at': self._now(),
            'engine_version': '',
            'rules_version': '',
            'hero_code': '',
            'hero_name': '',
            'villain_code': '',
            'villain_name': '',
            'scenario_name': '',
            'scenario_key': '',
            'expert': 0,
            'heroic': 0,
            'result': 'unknown',
            'game_over_reason': '',
            'rounds': None,
            'playtime_seconds': None,
            'seed': None,
            'campaign_id': '',
            'game_mode': 'quick',
            'deck_name': '',
            'deck_source': '',
            'remaining_hit_points': None,
            'minions_in_play': None,
            'side_schemes_in_play': None,
            'undo_count': None,
            'replay_file': '',
            'imported_from_replay': 0,
            'replay_analysis_status': '',
            'replay_analysis_error': '',
            'source': 'digital',
            'notes': '',
            'hero_rating': None,
            'scenario_rating': None,
            'is_service': 0,
            **record,
        }
        if not values['source_key']:
            raise ValueError('A game history source key is required.')
        if values['result'] not in self.KNOWN_RESULTS:
            values['result'] = 'unknown'
        if values['source'] not in self.KNOWN_SOURCES:
            raise ValueError('Unknown game source.')

        placeholders = ','.join('?' for _ in columns)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'INSERT OR IGNORE INTO games ({",".join(columns)}) '
                f'VALUES ({placeholders})',
                tuple(values[column] for column in columns),
            )
            inserted = bool(cursor.rowcount)
            row = connection.execute(
                'SELECT id, result FROM games WHERE source_key = ?',
                (values['source_key'],),
            ).fetchone()
            assert row is not None
            database_game_id = int(row['id'])

            # Who was in it. A record with no players named is a game from
            # before there could be more than one, so it takes the seat it
            # always implicitly had.
            seats = record.get('players') if isinstance(record, dict) else None
            if not seats:
                seats = [{
                    'seat': 0,
                    'hero_code': values['hero_code'],
                    'hero_name': values['hero_name'],
                    'deck_name': values['deck_name'],
                    'deck_source': values['deck_source'],
                }]
            connection.executemany(
                'INSERT OR REPLACE INTO game_players '
                '(game_id, seat, hero_code, hero_name, deck_name, deck_source) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                [
                    (
                        database_game_id,
                        int(seat.get('seat', index)),
                        str(seat.get('hero_code', '')),
                        str(seat.get('hero_name', '')),
                        str(seat.get('deck_name', '')),
                        str(seat.get('deck_source', '')),
                    )
                    for index, seat in enumerate(seats)
                ],
            )

            outcome_updated = False
            if not inserted and values.get('replay_file'):
                connection.execute(
                    'UPDATE games SET replay_file = ?, '
                    'playtime_seconds = COALESCE(?, playtime_seconds), '
                    'replay_analysis_status = ?, replay_analysis_error = ? '
                    'WHERE id = ?',
                    (
                        values['replay_file'],
                        values.get('playtime_seconds'),
                        values.get('replay_analysis_status', ''),
                        values.get('replay_analysis_error', ''),
                        database_game_id,
                    ),
                )

                if row['result'] == 'unknown' and values['result'] in ('win', 'loss'):
                    connection.execute(
                        'UPDATE games SET result = ?, game_over_reason = ?, '
                        'rounds = COALESCE(?, rounds), '
                        'remaining_hit_points = COALESCE(?, remaining_hit_points), '
                        'minions_in_play = COALESCE(?, minions_in_play), '
                        'side_schemes_in_play = COALESCE(?, side_schemes_in_play) '
                        'WHERE id = ?',
                        (
                            values['result'],
                            values.get('game_over_reason', ''),
                            values.get('rounds'),
                            values.get('remaining_hit_points'),
                            values.get('minions_in_play'),
                            values.get('side_schemes_in_play'),
                            database_game_id,
                        ),
                    )
                    outcome_updated = True

            if inserted and card_statistics:
                connection.executemany(
                    'INSERT INTO game_card_statistics '
                    '(game_id, card_id, card_name, damage_dealt, damage_taken, '
                    'thwarted_threat, entered_play) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    [(
                        database_game_id,
                        item['card_id'],
                        item['card_name'],
                        item['damage_dealt'],
                        item['damage_taken'],
                        item['thwarted_threat'],
                        item['entered_play'],
                    ) for item in card_statistics],
                )

            unlocked = AchievementEvaluator.UnlockEarned(
                connection,
                database_game_id,
                str(values['finished_at']),
            ) if (inserted or outcome_updated) and values['result'] in ('win', 'loss') else []
            return {
                'inserted': inserted,
                'updated': outcome_updated,
                'id': database_game_id,
                'unlocked': unlocked,
            }

    @staticmethod
    def _file_hash(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, 'rb') as file:
            for block in iter(lambda: file.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()

    def _record_from_replay(self, file_path: str) -> Dict[str, Any]:
        if os.path.getsize(file_path) > 100 * 1024 * 1024:
            raise ValueError('Replay is too large to import.')
        with open(file_path, encoding='utf-8') as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise ValueError('Replay root is not a JSON object.')

        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), dict) else {}
        campaign = raw.get('campaign') if isinstance(raw.get('campaign'), dict) else {}
        players = raw.get('players') if isinstance(raw.get('players'), list) else []
        # The same bound as a live game, and for the same reason: a replay
        # naming more players than the game supports was not produced by it.
        if not 1 <= len(players) <= self.MAX_PLAYERS:
            raise ValueError(
                f'Replays of more than {self.MAX_PLAYERS} players are not '
                'game history.')
        if raw.get('puzzle') or metadata.get('is_puzzle'):
            raise ValueError('Puzzle replays are not game history.')
        if (
            metadata.get('statistics_eligible') is False
            or metadata.get('statistics_excluded') is True
        ):
            raise ValueError('Replay is marked as ineligible for statistics.')
        if '-debug' in os.path.basename(file_path).lower():
            raise ValueError('Debug replays are not game history.')
        player = players[0] if players and isinstance(players[0], dict) else {}
        rules = raw.get('rules') if isinstance(raw.get('rules'), list) else []
        replay_game_id = str(metadata.get('game_id', '')).strip()
        source_key = (
            f'game:{replay_game_id}'
            if replay_game_id
            else f'replay:{self._file_hash(file_path)}'
        )
        result = str(metadata.get('game_result', 'unknown')).lower()
        if result not in ('win', 'loss'):
            result = 'unknown'
        villain_code = self._first_card_id(
            campaign.get('villain') or campaign.get('schemes')
        )
        scenario_name = str(campaign.get('name', '') or villain_code)
        player_metadata = player.get('metadata') if isinstance(player.get('metadata'), dict) else {}
        saved_time = self._normalize_finished_at(metadata.get('time'), file_path)
        seats = [
            {
                'seat': seat,
                'hero_code': self._first_card_id(seated.get('hero')),
                'hero_name': str(seated.get('name', '')),
                'deck_name': str(
                    seated.get('deck_name', '') or seated.get('name', '')),
                'deck_source': str(
                    (seated.get('metadata') or {}).get(
                        'source',
                        (seated.get('metadata') or {}).get('url', 'replay'),
                    )
                ),
            }
            for seat, seated in enumerate(players)
            if isinstance(seated, dict)
        ]
        return {
            'players': seats,
            'source_key': source_key,
            'finished_at': saved_time,
            'engine_version': str(raw.get('version', '')),
            'rules_version': 'v18' if 'v18_all' in rules else 'legacy',
            'hero_code': self._first_card_id(player.get('hero')),
            'hero_name': str(player.get('name', '')),
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': self._slug(scenario_name),
            'expert': int(bool(campaign.get('expert', False))),
            'heroic': self.HeroicLevel(rules),
            'result': result,
            'game_over_reason': str(metadata.get('game_over_reason', '')),
            'rounds': self._safe_int(metadata.get('rounds')),
            'playtime_seconds': self._safe_float(metadata.get('playtime')),
            'seed': self._safe_int(metadata.get('seed')),
            'campaign_id': str(campaign.get('campaign_id', '')),
            'game_mode': 'campaign' if 'mode_campaign' in rules else 'quick',
            'deck_name': str(player.get('deck_name', '') or player.get('name', '')),
            'deck_source': str(player_metadata.get('source', player_metadata.get('url', 'replay'))),
            'remaining_hit_points': self._safe_int(metadata.get('remaining_hit_points')),
            'minions_in_play': self._safe_int(metadata.get('minions_in_play')),
            'side_schemes_in_play': self._safe_int(metadata.get('side_schemes_in_play')),
            'undo_count': self._safe_int(metadata.get('undo_count')),
            'replay_file': os.path.abspath(file_path),
            'imported_from_replay': 1,
            'replay_analysis_status': 'metadata' if result in ('win', 'loss') else 'pending',
            'replay_analysis_error': '',
            'source': 'replay_import',
            'notes': '',
        }

    def _existing_replay_state(self, source_key: str) -> Dict[str, str]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                'SELECT result, replay_analysis_status, replay_analysis_error '
                'FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone()
            return {
                'result': str(row['result']),
                'status': str(row['replay_analysis_status']),
                'error': str(row['replay_analysis_error']),
            } if row else {'result': '', 'status': '', 'error': ''}

    def ImportReplays(
        self,
        outcome_analyzer: 'ReplayOutcomeAnalyzer|None'=None,
    ) -> int:
        if not self.available:
            return 0
        records: List[Dict[str, Any]] = []
        for file_path in FileManager.ListFiles(
            *self.replay_folders,
            ext='.json',
        ):
            try:
                record = self._record_from_replay(file_path)
                existing = self._existing_replay_state(str(record['source_key']))
                existing_result = existing['result']
                if existing_result in ('win', 'loss'):
                    record['result'] = existing_result
                    record['replay_analysis_status'] = existing['status']
                    record['replay_analysis_error'] = existing['error']
                elif record['result'] == 'unknown':
                    if record['rules_version'] != 'v18':
                        from game.scene.loader import UnsupportedReplayRulesError
                        record['replay_analysis_status'] = 'unsupported'
                        record['replay_analysis_error'] = UnsupportedReplayRulesError.MESSAGE
                    elif outcome_analyzer:
                        try:
                            outcome = outcome_analyzer.Analyze(file_path)
                            record.update(outcome.AsRecord())
                            record['replay_analysis_status'] = 'resolved'
                            record['replay_analysis_error'] = ''
                        except Exception as exc:
                            record['replay_analysis_status'] = 'failed'
                            record['replay_analysis_error'] = str(exc)
                            Log.Warn(
                                CATEGORY_NAME,
                                f'Could not determine replay outcome {file_path}: {exc}',
                            )
                records.append(record)
            except Exception as exc:
                Log.Warn(
                    CATEGORY_NAME,
                    f'Could not import replay {file_path}: {exc}',
                )

        # Achievement streaks and unlock timestamps depend on game order.
        # Replay folders are not guaranteed to be listed chronologically.
        records.sort(key=lambda record: str(record['finished_at']))
        imported = 0
        for record in records:
            result = self._store_game(record)
            imported += int(bool(result['inserted']))
        return imported

    @staticmethod
    def _rate(wins: int, games: int) -> float:
        return round(wins * 100.0 / games, 1) if games else 0.0

    @staticmethod
    def _normalize_source_filter(source: str) -> str:
        source = str(source or 'all').strip().lower()
        if source not in ('all', *GameHistory.KNOWN_SOURCES):
            raise ValueError('Unknown game history source filter.')
        return source

    @staticmethod
    def _normalize_physical_date(value: Any) -> str:
        text = str(value or '').strip()
        if not text:
            return GameHistory._now()
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError('Played date is invalid.') from exc
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed.isoformat()

    @staticmethod
    def _required_text(data: Dict[str, Any], key: str, label: str, limit: int) -> str:
        value = str(data.get(key, '')).strip()
        if not value:
            raise ValueError(f'{label} is required.')
        if len(value) > limit:
            raise ValueError(f'{label} is too long.')
        return value

    def SavePhysicalGame(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError('Game history is unavailable.')
        if not isinstance(data, dict):
            raise ValueError('Expected a physical game object.')

        hero_name = self._required_text(data, 'hero_name', 'Hero', 120)
        scenario_name = self._required_text(data, 'scenario_name', 'Scenario', 160)
        result = str(data.get('result', '')).strip().lower()
        if result not in ('win', 'loss'):
            raise ValueError('Result must be win or loss.')
        rounds = self._safe_int(data.get('rounds'))
        if rounds is not None and not 1 <= rounds <= 999:
            raise ValueError('Rounds must be between 1 and 999.')
        playtime_minutes = self._safe_float(data.get('playtime_minutes'))
        if playtime_minutes is not None and not 0 <= playtime_minutes <= 100000:
            raise ValueError('Play time is invalid.')
        remaining_hit_points = self._safe_int(data.get('remaining_hit_points'))
        if remaining_hit_points is not None and not 0 <= remaining_hit_points <= 999:
            raise ValueError('Remaining hit points are invalid.')
        clean_table = data.get('clean_table') is True
        notes = str(data.get('notes', '')).strip()
        if len(notes) > 4000:
            raise ValueError('Notes are too long.')
        deck_name = str(data.get('deck_name', '')).strip()
        if len(deck_name) > 200:
            raise ValueError('Deck name is too long.')

        finished_at = self._normalize_physical_date(data.get('finished_at'))
        hero_code = str(data.get('hero_code', '')).strip()[:80]
        villain_code = str(data.get('villain_code', '')).strip()[:80]
        scenario_key = str(data.get('scenario_key', '')).strip()
        if not scenario_key:
            scenario_key = self._slug(scenario_name)
        if len(scenario_key) > 160:
            raise ValueError('Scenario key is too long.')

        record = {
            'finished_at': finished_at,
            'engine_version': '',
            'rules_version': 'v18',
            'hero_code': hero_code,
            'hero_name': hero_name,
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': scenario_key,
            'expert': int(bool(data.get('expert', False))),
            'heroic': max(0, int(data.get('heroic', 0) or 0)),
            'result': result,
            'game_over_reason': '',
            'rounds': rounds,
            'playtime_seconds': (
                playtime_minutes * 60 if playtime_minutes is not None else None
            ),
            'campaign_id': '',
            'game_mode': 'physical',
            'deck_name': deck_name,
            'deck_source': 'physical',
            'remaining_hit_points': remaining_hit_points,
            'minions_in_play': 0 if clean_table else None,
            'side_schemes_in_play': 0 if clean_table else None,
            # A physical session does not have the engine's Undo command.
            'undo_count': 0,
            'replay_file': '',
            'imported_from_replay': 0,
            'source': 'physical',
            'notes': notes,
        }

        game_id = self._safe_int(data.get('id'))
        if game_id is None:
            record['source_key'] = f'physical:{uuid.uuid4().hex}'
            stored = self._store_game(record)
            return {
                'id': stored['id'],
                'created': True,
                'unlocked': stored['unlocked'],
            }

        columns = (
            'finished_at', 'hero_code', 'hero_name', 'villain_code',
            'villain_name', 'scenario_name', 'scenario_key', 'expert',
            'heroic', 'result',
            'rounds', 'playtime_seconds', 'deck_name', 'notes',
            'remaining_hit_points', 'minions_in_play',
            'side_schemes_in_play', 'undo_count',
        )
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'UPDATE games SET {", ".join(f"{column} = ?" for column in columns)} '
                "WHERE id = ? AND source = 'physical'",
                (*[record[column] for column in columns], game_id),
            )
            if not cursor.rowcount:
                raise ValueError('Physical game was not found.')
            unlocked = AchievementEvaluator.Recalculate(
                connection,
                game_id,
                finished_at,
            )
        return {'id': game_id, 'created': False, 'unlocked': unlocked}

    def DeletePhysicalGame(self, game_id: Any) -> Dict[str, Any]:
        parsed_id = self._safe_int(game_id)
        if parsed_id is None:
            raise ValueError('Physical game id is invalid.')
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM games WHERE id = ? AND source = 'physical'",
                (parsed_id,),
            )
            if not cursor.rowcount:
                raise ValueError('Physical game was not found.')
            AchievementEvaluator.Recalculate(connection)
        return {'deleted': True, 'id': parsed_id}

    def SaveCollection(self, product_keys: Any) -> Dict[str, Any]:
        if not isinstance(product_keys, list):
            raise ValueError('Owned products must be a list.')
        normalized: List[str] = []
        for value in product_keys:
            key = str(value).strip().lower()
            if not key or len(key) > 80 or not re.fullmatch(r'[a-z0-9_]+', key):
                raise ValueError('An owned product key is invalid.')
            if key not in normalized:
                normalized.append(key)
        now = self._now()
        with self._lock, self._connect() as connection:
            existing = {
                str(row['product_key']): str(row['owned_at'])
                for row in connection.execute(
                    'SELECT product_key, owned_at FROM collection_products'
                ).fetchall()
            }
            connection.execute('DELETE FROM collection_products')
            connection.executemany(
                'INSERT INTO collection_products '
                '(product_key, owned_at, updated_at) VALUES (?, ?, ?)',
                [(key, existing.get(key, now), now) for key in normalized],
            )
        return {'owned_products': normalized}

    def GetFavoriteDecks(self) -> List[str]:
        """Every starred deck, oldest star first."""
        if not self.available:
            return []
        with self._lock, self._connect() as connection:
            return [
                str(row['deck_id'])
                for row in connection.execute(
                    # Oldest star first, and within a single save the order it
                    # was sent in: everything saved together shares a
                    # timestamp, so rowid is what keeps a list from coming
                    # back alphabetised.
                    'SELECT deck_id FROM favorite_decks '
                    'ORDER BY favorited_at, rowid'
                ).fetchall()
            ]

    def SaveFavoriteDecks(self, deck_ids: Any) -> Dict[str, Any]:
        """Replace the starred decks with this list.

        Whole-list rather than one star at a time, the way the collection is
        saved: the browser holds the list anyway, and a replace cannot leave
        the two disagreeing about a star that failed to send.

        The id is the deck's file name, which is what both pickers already use
        to identify a deck.
        """
        if not isinstance(deck_ids, list):
            raise ValueError('Favourite decks must be a list.')
        normalized: List[str] = []
        for value in deck_ids:
            deck_id = str(value).strip()
            valid = re.fullmatch(r'[A-Za-z0-9_.\-]+', deck_id)
            if not deck_id or len(deck_id) > 120 or not valid:
                raise ValueError('A favourite deck id is invalid.')
            if deck_id not in normalized:
                normalized.append(deck_id)
        now = self._now()
        with self._lock, self._connect() as connection:
            # Keep the moment a deck was first starred, so the order a player
            # built the list up in survives a save that only adds to it.
            existing = {
                str(row['deck_id']): str(row['favorited_at'])
                for row in connection.execute(
                    'SELECT deck_id, favorited_at FROM favorite_decks'
                ).fetchall()
            }
            connection.execute('DELETE FROM favorite_decks')
            connection.executemany(
                'INSERT INTO favorite_decks (deck_id, favorited_at) VALUES (?, ?)',
                [(deck_id, existing.get(deck_id, now)) for deck_id in normalized],
            )
        return {'favorite_decks': normalized}

    @staticmethod
    def _rating_value(data: Dict[str, Any], key: str) -> int|None:
        value = data[key]
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError('Ratings must be whole numbers from 1 to 5.')
        return value

    def SaveGameRatings(self, source_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError('Game history is unavailable.')
        if not isinstance(data, dict):
            raise ValueError('Expected a game rating object.')

        allowed = ('hero_rating', 'scenario_rating')
        ratings = {
            key: self._rating_value(data, key)
            for key in allowed
            if key in data
        }
        if not ratings:
            raise ValueError('Choose a hero or scenario rating to save.')

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'UPDATE games SET {", ".join(f"{key} = ?" for key in ratings)} '
                "WHERE source_key = ? AND source = 'digital' "
                "AND result IN ('win', 'loss') AND is_service = 0",
                (*ratings.values(), source_key),
            )
            if not cursor.rowcount:
                raise ValueError('The completed digital game was not found.')
            row = connection.execute(
                'SELECT hero_rating, scenario_rating FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone()
        assert row is not None
        return {
            'saved': True,
            'hero_rating': row['hero_rating'],
            'scenario_rating': row['scenario_rating'],
        }

    def _EnsureCurrentGameStored(self, game: Any) -> str:
        """The finished game on the table as a history row, and its key.

        Recorded now if the end of the game has not got to it yet, so that
        anything done from the game-over screen -- a rating, a send to BG
        Stats -- finds the row it is about. Raises ValueError, with the
        reason, for a game that is not a completed, counted one.
        """
        world = game.world
        scene = game.session.scene
        if not world or not scene or not world.is_game_over:
            raise ValueError('There is no completed game.')
        if world.game_over.is_game_exit_or_undo:
            raise ValueError('Only a completed game counts.')
        if game.controller_manager.replay.is_replay or scene.is_puzzle:
            raise ValueError('Replay and puzzle sessions are not recorded.')
        if not scene.GetMetadataBool('statistics_eligible'):
            raise ValueError('This game is not eligible for statistics.')

        source_key = f'game:{self.EnsureSceneGameId(scene)}'
        with self._lock, self._connect() as connection:
            exists = connection.execute(
                'SELECT 1 FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone() is not None
        if not exists:
            self._store_game(self._live_record(game), self._live_card_statistics(game))
        return source_key

    def SaveCurrentGameRatings(self, game: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        source_key = self._EnsureCurrentGameStored(game)
        return self.SaveGameRatings(source_key, data)

    def CurrentGameRecord(self, game: Any) -> Dict[str, Any]:
        """The finished game on the table, in the history's own row shape.

        What the game-over screen hands to BG Stats: the same fields the
        history page's rows carry, so one sender serves both.
        """
        source_key = self._EnsureCurrentGameStored(game)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                'SELECT id, finished_at, hero_code, hero_name, villain_code, villain_name, '
                'expert, heroic, result, rounds, playtime_seconds, source, deck_name, notes, '
                + '(SELECT COUNT(*) FROM game_players p WHERE p.game_id = games.id) seats, '
                "(SELECT group_concat(hero_name, '／') FROM (SELECT hero_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) heroes, "
                "(SELECT group_concat(deck_name, '／') FROM (SELECT deck_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) decks "
                'FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone()
        if row is None:
            raise ValueError('The completed game could not be recorded.')
        return dict(row)

    def ImportTrackerGames(
        self,
        records: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Store converted tracker rows, skipping ones already held.

        Deduplication is the `source_key` unique index and nothing else: the
        caller builds that key from the play's own timestamp, hero and
        scenario, so re-importing the same export a second time inserts
        nothing. `_store_game` already inserts with OR IGNORE and reports
        whether a row was actually written.
        """
        if not self.available:
            return {'imported': 0, 'skipped': 0}
        imported = 0
        skipped = 0
        for record in records:
            stored = self._store_game(record)
            if stored.get('inserted'):
                imported += 1
            else:
                skipped += 1
        return {'imported': imported, 'skipped': skipped}

    def GetMatchupCounts(self, source: str = 'all') -> List[Dict[str, Any]]:
        """Games grouped by which hero met which scenario.

        The pairing is the whole point and no dashboard grouping carries it:
        those count heroes and scenarios on separate axes, so a hero with ten
        wins and a scenario with ten losses say nothing about whether the two
        ever sat down together. The composite index on
        (hero_code, scenario_key, expert, result) already covers this.

        Only decided games count. An abandoned or unknown result says nothing
        about how the matchup went, and counting it as a play would make a
        coverage grid claim ground that was never actually held.
        """
        if not self.available:
            return []
        source = self._normalize_source_filter(source)
        with self._lock, self._connect() as connection:
            where = " WHERE g.is_service = 0 AND g.result IN ('win', 'loss')"
            parameters: tuple[Any, ...] = ()
            if source != 'all':
                where += ' AND g.source = ?'
                parameters = (source,)
            rows = connection.execute(
                'SELECT p.hero_code hero_code, g.scenario_key scenario_key, '
                'COUNT(*) games, '
                "SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END) wins, "
                'SUM(g.expert) expert_games, '
                "SUM(CASE WHEN g.expert = 1 AND g.result = 'win' THEN 1 ELSE 0 END) "
                'expert_wins, '
                # The best this pairing has been beaten at, on one ladder:
                # 0 never, 1 Standard, 2 Expert, 3+ Heroic at level - 2.
                #
                # Heroic outranks Expert, and a Heroic win scores by its level
                # whether or not Expert was also on -- the extra encounter card
                # per level is the thing being measured, and stacking the two
                # would put Expert + Heroic 1 level with Heroic 2, which it is
                # not. MAX over wins only: losing at Heroic says you tried it,
                # not that you cleared it.
                "MAX(CASE WHEN g.result != 'win' THEN 0 "
                'WHEN g.heroic > 0 THEN 2 + g.heroic '
                'WHEN g.expert = 1 THEN 2 '
                'ELSE 1 END) best_beaten, '
                'MAX(g.heroic) heroic_played, '
                "MAX(CASE WHEN g.result = 'win' THEN g.heroic ELSE 0 END) heroic_beaten "

                # Through the seats, so a two-handed win lands on the row of
                # each hero who was there rather than only the first.
                'FROM game_players p JOIN games g ON g.id = p.game_id'
                f'{where} '
                'GROUP BY p.hero_code, g.scenario_key',
                parameters,
            ).fetchall()
        return [
            {
                'hero_code': str(row['hero_code'] or ''),
                'scenario_key': str(row['scenario_key'] or ''),
                'games': int(row['games'] or 0),
                'wins': int(row['wins'] or 0),
                'expert_games': int(row['expert_games'] or 0),
                'expert_wins': int(row['expert_wins'] or 0),
                # 0 not beaten, 1 Standard, 2 Expert, 3+ Heroic (level = value - 2).
                'best_beaten': int(row['best_beaten'] or 0),
                'heroic_played': int(row['heroic_played'] or 0),
                'heroic_beaten': int(row['heroic_beaten'] or 0),
            }
            for row in rows
        ]

    def GetDeckRecords(self, source: str='all') -> Dict[str, Any]:
        """Win-loss records keyed by hero identity and by deck name.

        For the deck viewer, which asks about one deck at a time. The
        dashboard already groups by hero, but it also carries a hundred recent
        games, every achievement and the collection, so a page that wants two
        numbers asks here instead.

        Decks are grouped by the name recorded with the game, which is what
        the viewer shows in its list -- so two different decks sharing a name
        share a record. Deliberate: the name is all a finished game keeps of
        which deck was played, and a wrong split would be worse than a merge.
        """
        if not self.available:
            return {'available': False, 'error': 'Game history is unavailable.'}
        source = self._normalize_source_filter(source)
        with self._lock, self._connect() as connection:
            parameters: tuple[Any, ...] = () if source == 'all' else (source,)
            source_clause = 'AND g.source = ? ' if source != 'all' else ''

            def grouped(query: str) -> List[Dict[str, Any]]:
                rows: List[Dict[str, Any]] = []
                for row in connection.execute(query, parameters).fetchall():
                    item = dict(row)
                    games = int(item.pop('games'))
                    item['games'] = games
                    item['wins'] = int(item['wins'])
                    item['losses'] = games - item['wins']
                    item['win_rate'] = self._rate(item['wins'], games)
                    rows.append(item)
                return rows

            seated = ('FROM game_players p JOIN games g ON g.id = p.game_id '
                      "WHERE g.is_service = 0 AND g.result IN ('win', 'loss') ")
            heroes = grouped(
                'SELECT p.hero_code hero_code, MAX(p.hero_name) hero_name, '
                'COUNT(*) games, '
                "SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END) wins "
                + seated +
                "AND p.hero_code != '' "
                + source_clause +
                'GROUP BY p.hero_code ORDER BY games DESC, hero_name'
            )
            decks = grouped(
                'SELECT p.deck_name deck_name, MAX(p.hero_code) hero_code, '
                'COUNT(*) games, '
                "SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END) wins "
                + seated +
                "AND p.deck_name != '' "
                + source_clause +
                'GROUP BY p.deck_name ORDER BY games DESC, deck_name'
            )
            return {
                'available': True,
                'source_filter': source,
                'heroes': heroes,
                'decks': decks,
            }

    def DecidedGames(self, source: str='all', ids: Sequence[int]|None=None) -> List[Dict[str, Any]]:
        """Won or lost games, oldest first, for a play file.

        `ids` narrows it to the games the player ticked; an id that is not a
        decided game in this view is simply not in the answer. Abandoned and
        unknown games stay out either way, as they do from the BG Stats
        button, since they would arrive as losses.
        """
        if not self.available:
            return []
        source = self._normalize_source_filter(source)
        wanted = [int(value) for value in ids] if ids is not None else None
        if wanted is not None and not wanted:
            return []
        with self._lock, self._connect() as connection:
            parameters: List[Any] = [] if source == 'all' else [source]
            where = ''
            if wanted is not None:
                where = 'AND id IN (' + ','.join('?' * len(wanted)) + ') '
                parameters.extend(wanted)
            return [dict(row) for row in connection.execute(
                'SELECT id, finished_at, hero_code, hero_name, villain_code, villain_name, '
                'expert, heroic, result, rounds, playtime_seconds, deck_name, notes, '
                + '(SELECT COUNT(*) FROM game_players p WHERE p.game_id = games.id) seats, '
                "(SELECT group_concat(hero_name, '／') FROM (SELECT hero_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) heroes, "
                "(SELECT group_concat(deck_name, '／') FROM (SELECT deck_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) decks "
                "FROM games WHERE is_service = 0 AND result IN ('win', 'loss') "
                + ("AND source = ? " if source != 'all' else '') + where +
                'ORDER BY datetime(finished_at), id',
                parameters,
            ).fetchall()]

    def GetDashboard(self, source: str='all') -> Dict[str, Any]:
        if not self.available:
            return {'available': False, 'error': 'Game history is unavailable.'}
        source = self._normalize_source_filter(source)
        with self._lock, self._connect() as connection:
            where = ' WHERE is_service = 0'
            if source != 'all':
                where += ' AND source = ?'
            parameters: tuple[Any, ...] = () if source == 'all' else (source,)
            overview_row = connection.execute(
                'SELECT '
                "SUM(CASE WHEN result IN ('win', 'loss') THEN 1 ELSE 0 END) completed, "
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins, "
                "SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) losses, "
                "SUM(CASE WHEN result = 'unknown' THEN 1 ELSE 0 END) unknown_games, "
                "AVG(CASE WHEN result IN ('win', 'loss') THEN rounds END) average_rounds, "
                "AVG(CASE WHEN result IN ('win', 'loss') THEN playtime_seconds END) average_playtime "
                f'FROM games{where}',
                parameters,
            ).fetchone()
            completed = int(overview_row['completed'] or 0)
            wins = int(overview_row['wins'] or 0)

            def grouped(query: str) -> List[Dict[str, Any]]:
                rows: List[Dict[str, Any]] = []
                for row in connection.execute(query, parameters).fetchall():
                    item = dict(row)
                    games = int(item.pop('games'))
                    item['games'] = games
                    item['wins'] = int(item['wins'])
                    item['losses'] = games - item['wins']
                    item['win_rate'] = self._rate(item['wins'], games)
                    rows.append(item)
                return rows

            heroes = grouped(
                # Through the seats: a two-handed game is one game and two
                # heroes, and each of them played it.
                'SELECT p.hero_code hero_code, MAX(p.hero_name) hero_name, '
                'COUNT(*) games, '
                "SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END) wins, "
                'ROUND(AVG(g.hero_rating), 2) average_rating, '
                'COUNT(g.hero_rating) rating_count '
                'FROM game_players p JOIN games g ON g.id = p.game_id '
                "WHERE g.is_service = 0 AND g.result IN ('win', 'loss') "
                + ("AND g.source = ? " if source != 'all' else '') +
                'GROUP BY p.hero_code ORDER BY games DESC, hero_name'
            )
            villains = grouped(
                'SELECT MAX(villain_code) villain_code, '
                'MAX(villain_name) villain_name, COUNT(*) games, '
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins, "
                'ROUND(AVG(scenario_rating), 2) average_rating, '
                'COUNT(scenario_rating) rating_count '
                "FROM games WHERE is_service = 0 AND result IN ('win', 'loss') "
                + ("AND source = ? " if source != 'all' else '') +
                'GROUP BY scenario_key ORDER BY games DESC, villain_name'
            )
            matchups = grouped(
                'SELECT p.hero_code hero_code, MAX(p.hero_name) hero_name, '
                'MAX(g.villain_code) villain_code, '
                'MAX(g.villain_name) villain_name, g.expert expert, '
                'COUNT(*) games, '
                "SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END) wins "
                'FROM game_players p JOIN games g ON g.id = p.game_id '
                "WHERE g.is_service = 0 AND g.result IN ('win', 'loss') "
                + ("AND g.source = ? " if source != 'all' else '') +
                'GROUP BY p.hero_code, g.scenario_key, g.expert '
                'ORDER BY games DESC, hero_name, villain_name, expert'
            )
            # Every seat, in order, beside the row: a two-handed game is one
            # game with two heroes in it, and the list should say so.
            recent = [dict(row) for row in connection.execute(
                'SELECT id, finished_at, hero_code, hero_name, villain_code, scenario_key, '
                'villain_name, expert, heroic, result, rounds, playtime_seconds, '
                'game_over_reason, replay_file, replay_analysis_status, '
                'replay_analysis_error, source, deck_name, notes, '
                'remaining_hit_points, minions_in_play, side_schemes_in_play, '
                'hero_rating, scenario_rating, '
                + '(SELECT COUNT(*) FROM game_players p WHERE p.game_id = games.id) seats, '
                "(SELECT group_concat(hero_name, '／') FROM (SELECT hero_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) heroes, "
                "(SELECT group_concat(deck_name, '／') FROM (SELECT deck_name FROM game_players p WHERE p.game_id = games.id ORDER BY seat)) decks "
                'FROM games WHERE is_service = 0 '
                + ("AND source = ? " if source != 'all' else '') +
                'ORDER BY datetime(finished_at) DESC, id DESC LIMIT 100',
                parameters,
            ).fetchall()]
            owned_products = [
                str(row['product_key'])
                for row in connection.execute(
                    'SELECT product_key FROM collection_products '
                    'ORDER BY product_key'
                ).fetchall()
            ]
            return {
                'available': True,
                'source_filter': source,
                'overview': {
                    'completed': completed,
                    'wins': wins,
                    'losses': int(overview_row['losses'] or 0),
                    'win_rate': self._rate(wins, completed),
                    'unknown_games': int(overview_row['unknown_games'] or 0),
                    'average_rounds': round(float(overview_row['average_rounds'] or 0), 1),
                    'average_playtime': round(float(overview_row['average_playtime'] or 0), 1),
                },
                'heroes': heroes,
                'villains': villains,
                'matchups': matchups,
                'recent_games': recent,
                'achievements': AchievementEvaluator.Dashboard(connection),
                'owned_products': owned_products,
            }
