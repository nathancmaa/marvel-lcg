"""Cerebro's play history through the Nexus sync server.

Nexus (marvel-lcg-phoenix) keeps every device's play data on one small server
on the home network (its docs/nexus-sync.md). Cerebro is one more client of
it, for Marvel Champions games only: `mc/game/<source_key>`, whose body is the
game's row as Phoenix's `History::sync_rows` writes it (GameHistory.SyncRows
makes the same text). This mirrors Nexus's own client, godot/scripts/
nexus_sync.gd: each run scans the history, queues what changed with a
hybrid-logical-clock stamp, pushes the queue, then pulls what other devices
changed from the last cursor.

Where Cerebro departs from it, on purpose:

- Its history holds games that exist nowhere else, so its very first sync
  pulls before it queues anything. A game the server already has with the
  same text is simply marked synced. Where the texts differ, the game's
  origin decides: `phoenix:` keys are Phoenix's, so the server's text is
  taken; every other key (`physical:` too) is Cerebro's own, so Cerebro's text
  is sent again with a fresh stamp and wins. The losing text is kept in
  `sync-conflicts/` either way. After that first sync the newest stamp wins,
  as everywhere else.
- Nothing is overwritten or removed without a copy: before a pulled version
  replaces a game held here, its text goes to `sync-conflicts/`, and before a
  pulled deletion removes one, to `sync-trash/`.
- Before the first sync it ever makes, it takes an SQLite backup of the
  history beside it (`statistics.pre-nexus-sync.sqlite3`), once.

Everything lives beside the history database (`runtime/` on the NAS):
`nexus-sync-state.json` (device id, clock, cursor, what was last synced),
`nexus-sync-outbox.json` (stamped changes still to send), and the two
folders above.

With no address or no secret, nothing here runs at all.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import urllib.error
import urllib.request

from engine.config import ConfigVariables
from engine.log import Log

if TYPE_CHECKING:
    from game.statistics.game_history import GameHistory


CATEGORY_NAME = 'STATISTICS'

# `-nexus_sync_address 10.1.2.250:8781` or launch.json override the
# environment, as for any setting. The secret is better left to the
# environment: a command line is visible to everyone on the machine.
NEXUS_SYNC_ADDRESS = ConfigVariables.Str(
    'nexus_sync_address', os.environ.get('NEXUS_SYNC_ADDRESS', ''))
NEXUS_SYNC_SECRET = ConfigVariables.Str(
    'nexus_sync_secret', os.environ.get('NEXUS_SYNC_SECRET', ''))

GAME = 'mc'
KIND = 'game'
# Keys Phoenix made. Every other key, `physical:` table games included
# (owner's decision, 2026-11-25), is a game Cerebro owns.
PHOENIX_ORIGIN = ('phoenix:',)


class SyncFailed(Exception):
    """A run that couldn't finish; the message is the status line."""


def RecordId(key: str) -> str:
    return f'{GAME}/{KIND}/{key}'


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _newer(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (int(a['hlc']), str(a['device'])) > (int(b['hlc']), str(b['device']))


def _cerebro_origin(key: str) -> bool:
    return not key.startswith(PHOENIX_ORIGIN)


class NexusSync:
    RETRY = (30.0, 60.0, 120.0, 300.0)
    EVERY = 300.0
    PUSH_BATCH = 200
    PUSH_BYTES = 8 * 1024 * 1024
    PULL_LIMIT = 500  # the server's own default page
    # A scan missing more than this many games at once, and more than a tenth
    # of them, is taken as lost local data: no deletions are sent, the games
    # are pulled back.
    LOSS_GUARD = 3
    STATE_FILE = 'nexus-sync-state.json'
    OUTBOX_FILE = 'nexus-sync-outbox.json'
    CONFLICTS_FOLDER = 'sync-conflicts'
    # Kept-aside conflict texts older than this are removed at each run (the
    # server still holds every version under /v1/revisions). sync-trash/ is
    # kept: deletions are rare.
    CONFLICTS_KEEP_DAYS = 30
    TRASH_FOLDER = 'sync-trash'
    BACKUP_SUFFIX = '.pre-nexus-sync.sqlite3'

    def __init__(
        self,
        history: 'GameHistory',
        address: str,
        secret: str,
        state_folder: str|None=None,
        timeout: float=20.0,
    ) -> None:
        self.history = history
        self.address = address.strip().rstrip('/')
        self.secret = secret.strip()
        self.state_folder = state_folder or os.path.dirname(
            os.path.abspath(history.file_path))
        self.timeout = timeout
        self.status = ''
        self.last_ok = 0.0
        self.last_summary: Dict[str, Any] = {}
        self._state: Dict[str, Any] = {}
        self._outbox: Dict[str, Dict[str, Any]] = {}
        self._run_lock = threading.Lock()
        self._failures = 0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread|None = None
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def FromConfig(cls, history: 'GameHistory') -> 'NexusSync|None':
        """The configured client, or None when sync is switched off."""
        address = str(NEXUS_SYNC_ADDRESS.value or '').strip()
        secret = str(NEXUS_SYNC_SECRET.value or '').strip()
        if not address or not secret or not history.available:
            return None
        return cls(history, address, secret)

    @property
    def configured(self) -> bool:
        return bool(self.address and self.secret)

    def base_url(self) -> str:
        if self.address.startswith(('http://', 'https://')):
            return self.address
        return 'http://' + self.address

    ############################################################################
    # The background loop: at start, on request, every five minutes, and
    # sooner again after a failure.

    def Start(self) -> None:
        if self._thread is not None or not self.configured:
            return
        self._thread = threading.Thread(target=self._loop, name='NexusSync', daemon=True)
        self._thread.start()

    def Request(self) -> None:
        """A run now, or once more after the one under way."""
        self._wake.set()

    def Stop(self, timeout: float=5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            # A request in flight can hold the thread for `timeout`; it is a
            # daemon, so it never keeps the process from ending.
            self._thread.join(timeout)
            self._thread = None

    def _loop(self) -> None:
        delay = 0.0
        while True:
            self._wake.wait(delay)
            if self._stop.is_set():
                return
            self._wake.clear()
            ok = self.Sync()
            delay = self.EVERY if ok else self.RETRY[min(self._failures, len(self.RETRY)) - 1]

    ############################################################################
    # One run

    def Sync(self) -> bool:
        """One full run. True when it reached the server and finished."""
        if not self.configured:
            return False
        with self._run_lock:
            try:
                summary = self._run()
            except SyncFailed as exc:
                return self._fail(str(exc))
            except Exception as exc:
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
                return self._fail(f'Sync stopped: {exc}')
        self._failures = 0
        self.last_ok = time.time()
        self.last_summary = summary
        words = []
        if summary['pushed']:
            words.append(f'{summary["pushed"]} sent')
        if summary['pulled']:
            words.append(f'{summary["pulled"]} received')
        if summary['conflicts']:
            words.append(f'{summary["conflicts"]} kept aside as conflicts')
        self.status = 'Synced' + (': ' + ', '.join(words) + '.' if words else ', nothing new.')
        if words:
            Log.Info(CATEGORY_NAME, f'Nexus sync: {self.status}')
        return True

    def _fail(self, why: str) -> bool:
        self._failures += 1
        if self._state:
            self._save_state()
        self.status = why
        Log.Info(CATEGORY_NAME, f'Nexus sync: {why}')
        return False

    def Queued(self) -> int:
        """How many games wait to be sent."""
        return len(self._outbox)

    def _run(self) -> Dict[str, Any]:
        if not self.history.available:
            raise SyncFailed('Game history is unavailable.')
        self._load_state()
        if not self._state['server_id']:
            self._backup()
        self._prune_conflicts()
        summary: Dict[str, Any] = {'pushed': 0, 'pulled': 0, 'unlocked': [], 'conflicts': 0}
        # Stamped before the server is asked, so a game played while it is
        # away is ordered by when it was played, however long it waits.
        local = self._scan() if self._state['first_done'] else {}
        health = self._call('GET', '/v1/health')
        server_id = str(health.get('server_id', ''))
        if not server_id:
            raise SyncFailed('The sync server gave no server id.')
        if self._state['server_id'] != server_id:
            if self._state['server_id']:
                self._forget_server()
                if self._state['first_done']:
                    local = self._scan()
            self._state['server_id'] = server_id
        if not self._state['first_done']:
            self._first_pull(summary)
            self._state['first_done'] = True
            self._save_state()
            local = self._scan()

        cursor = int(self._state['cursor'])
        pending = sorted(self._outbox)
        first = True
        while first or pending:
            first = False
            push: List[Dict[str, Any]] = []
            size = 0
            while pending and len(push) < self.PUSH_BATCH and size < self.PUSH_BYTES:
                record_id = pending.pop(0)
                entry = self._outbox[record_id]
                change = {
                    'game': GAME, 'kind': KIND, 'key': record_id.split('/', 2)[2],
                    'hlc': int(entry['hlc']), 'device': str(entry['device']),
                    'deleted': bool(entry['deleted']), 'body': None,
                }
                if not entry['deleted']:
                    text = local.get(record_id)
                    if text is None or _hash(text) != entry['hash']:
                        continue  # changed again since it was queued: the next scan stamps it anew
                    change['body'] = text
                    size += len(text.encode('utf-8'))
                push.append(change)
            reply = self._exchange(cursor, push)
            sent = {RecordId(change['key']): change for change in push}
            for result in reply.get('results', []):
                record_id = str(result.get('id', ''))
                change = sent.get(record_id)
                if change is None:
                    continue
                self._outbox.pop(record_id, None)
                if result.get('won'):
                    self._state['synced'][record_id] = {
                        'hash': 'deleted' if change['deleted'] else _hash(change['body']),
                        'hlc': change['hlc'], 'device': change['device'],
                    }
                    summary['pushed'] += 1
            cursor = self._take(reply, local, summary, cursor)

        # The rest of what other devices changed.
        more = True
        while more:
            reply = self._exchange(cursor, [])
            cursor = self._take(reply, local, summary, cursor)
            more = bool(reply.get('more', False))
        self._save_state()
        return summary

    def _exchange(self, cursor: int, push: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sends `push` and takes the changes after `cursor`, a page at a time."""
        return self._call('POST', '/v1/sync', {
            'device': self._state['device'], 'since': cursor, 'push': push,
            'limit': self.PULL_LIMIT,
        })

    def _check_server(self, reply: Dict[str, Any]) -> None:
        if str(reply.get('server_id', '')) != self._state['server_id']:
            raise SyncFailed('The server changed during a sync.')

    @staticmethod
    def _version(change: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'hash': str(change.get('hash', '')),
            'hlc': int(change.get('hlc', 0)),
            'device': str(change.get('device', '')),
        }

    @staticmethod
    def _ours(change: Dict[str, Any]) -> bool:
        return change.get('game') == GAME and change.get('kind') == KIND and \
            isinstance(change.get('key'), str) and bool(change.get('key'))

    def _take(
        self,
        reply: Dict[str, Any],
        local: Dict[str, str],
        summary: Dict[str, Any],
        cursor: int,
    ) -> int:
        """Applies one reply's changes (last writer wins); returns the new cursor."""
        self._check_server(reply)
        ready: List[Dict[str, Any]] = []
        for change in reply.get('changes', []):
            self._observe(int(change.get('hlc', 0)))
            if not self._ours(change):
                continue
            record_id = RecordId(change['key'])
            version = self._version(change)
            deleted = bool(change.get('deleted'))
            here = local.get(record_id)
            same = here is None if deleted else (here is not None and _hash(here) == version['hash'])
            queued = self._outbox.get(record_id)
            if queued and _newer(queued, version):
                continue  # this device's version, still to be sent, will win
            self._outbox.pop(record_id, None)
            if same:
                self._state['synced'][record_id] = version
                continue
            known = self._state['synced'].get(record_id, {}).get('hash', '')
            ready.append({
                'id': record_id, 'key': change['key'], 'deleted': deleted,
                'body': None if deleted else change.get('body'), 'version': version,
                'local_changed': here is not None and _hash(here) != known,
            })
        self._apply(ready, local, summary)
        self._state['cursor'] = int(reply.get('seq', cursor))
        self._save_state()
        return int(self._state['cursor'])

    def _first_pull(self, summary: Dict[str, Any]) -> None:
        """The first sync with a server: pull everything before queuing anything.

        Queuing first, as Nexus's client does, would stamp every game held here
        as new and let it replace whatever the server had. Instead each game
        the server holds is compared with the one here, and where they differ
        its origin decides which text stays (see the module's docstring).
        """
        local = {RecordId(key): text for key, text in self.history.SyncRows().items()}
        cursor = int(self._state['cursor'])
        more = True
        while more:
            reply = self._exchange(cursor, [])
            self._check_server(reply)
            ready: List[Dict[str, Any]] = []
            for change in reply.get('changes', []):
                self._observe(int(change.get('hlc', 0)))
                if not self._ours(change):
                    continue
                key = change['key']
                record_id = RecordId(key)
                version = self._version(change)
                deleted = bool(change.get('deleted'))
                here = local.get(record_id)
                if here is None and deleted:
                    self._state['synced'][record_id] = version
                    continue
                if here is not None and not deleted and _hash(here) == version['hash']:
                    self._state['synced'][record_id] = version
                    continue
                if here is not None and _cerebro_origin(key):
                    # Cerebro's game: its text here wins, and goes out again
                    # stamped after everything this pull has seen.
                    if not deleted and isinstance(change.get('body'), str):
                        self._keep_aside(
                            self.CONFLICTS_FOLDER, key,
                            f'from-{version["device"][:8]}-{version["hlc"]}',
                            change['body'],
                        )
                    self._outbox[record_id] = {
                        'hlc': self._tick(), 'device': self._state['device'],
                        'hash': _hash(here), 'deleted': False,
                    }
                    summary['conflicts'] += 1
                    continue
                ready.append({
                    'id': record_id, 'key': key, 'deleted': deleted,
                    'body': None if deleted else change.get('body'), 'version': version,
                    'local_changed': here is not None,
                })
            self._apply(ready, local, summary)
            cursor = int(reply.get('seq', cursor))
            self._state['cursor'] = cursor
            self._save_state()
            more = bool(reply.get('more', False))

    def _apply(
        self,
        changes: List[Dict[str, Any]],
        local: Dict[str, str],
        summary: Dict[str, Any],
    ) -> None:
        """Other devices' versions into the history, each held game copied first."""
        if not changes:
            return
        rows: List[Dict[str, Any]] = []
        deletes: List[str] = []
        applied: List[Dict[str, Any]] = []
        for change in changes:
            here = local.get(change['id'])
            if change['deleted']:
                if here is not None:
                    self._keep_aside(self.TRASH_FOLDER, change['key'], 'deleted', here)
                deletes.append(change['key'])
                applied.append(change)
                continue
            try:
                row = json.loads(change['body'])
            except (TypeError, ValueError):
                row = None
            if not isinstance(row, dict) or row.get('source_key') != change['key']:
                Log.Info(CATEGORY_NAME, f'Nexus sync: unreadable game {change["key"]} left out.')
                continue
            if here is not None:
                self._keep_aside(self.CONFLICTS_FOLDER, change['key'], 'here', here)
            rows.append(row)
            applied.append(change)
        outcome = self.history.ApplySync(rows, deletes)
        rejected = set(outcome.get('rejected', []))
        for change in applied:
            if change['key'] in rejected:
                continue
            self._state['synced'][change['id']] = change['version']
            if change['deleted']:
                local.pop(change['id'], None)
            else:
                local[change['id']] = change['body']
            if change['local_changed']:
                summary['conflicts'] += 1
            summary['pulled'] += 1
        summary['unlocked'].extend(outcome.get('unlocked', []))

    ############################################################################
    # The scan and the outbox

    def _scan(self) -> Dict[str, str]:
        """Every game as {record id: text}; queues what changed since the last sync."""
        local = {RecordId(key): text for key, text in self.history.SyncRows().items()}
        synced = self._state['synced']
        for record_id, text in local.items():
            digest = _hash(text)
            queued = self._outbox.get(record_id)
            known = queued['hash'] if queued else synced.get(record_id, {}).get('hash', '')
            if digest != known:
                self._outbox[record_id] = {
                    'hlc': self._tick(), 'device': self._state['device'],
                    'hash': digest, 'deleted': False,
                }
        gone = [
            record_id for record_id, kept in synced.items()
            if kept['hash'] != 'deleted' and record_id not in local
            and record_id not in self._outbox
        ]
        alive = sum(1 for kept in synced.values() if kept['hash'] != 'deleted')
        if len(gone) > self.LOSS_GUARD and len(gone) * 10 > alive:
            # Not deletions: the data went missing. Pull it all back.
            Log.Info(
                CATEGORY_NAME,
                f'Nexus sync: {len(gone)} games missing at once; pulling them back '
                'instead of deleting them everywhere.',
            )
            for record_id in gone:
                del synced[record_id]
            self._state['cursor'] = 0
        else:
            for record_id in gone:
                self._outbox[record_id] = {
                    'hlc': self._tick(), 'device': self._state['device'],
                    'hash': 'deleted', 'deleted': True,
                }
        self._save_state()
        return local

    def _forget_server(self) -> None:
        """A new or restored server: everything known goes again, with the versions it had."""
        for record_id, kept in self._state['synced'].items():
            if record_id not in self._outbox:
                self._outbox[record_id] = {
                    'hlc': int(kept['hlc']), 'device': str(kept['device']),
                    'hash': str(kept['hash']), 'deleted': kept['hash'] == 'deleted',
                }
        self._state['synced'] = {}
        self._state['cursor'] = 0

    def _tick(self) -> int:
        self._state['hlc'] = max(int(time.time() * 1000), int(self._state['hlc']) + 1)
        return int(self._state['hlc'])

    def _observe(self, stamp: int) -> None:
        self._state['hlc'] = max(int(self._state['hlc']), stamp)

    ############################################################################
    # Files beside the history

    def _path(self, *names: str) -> str:
        return os.path.join(self.state_folder, *names)

    def _backup(self) -> None:
        """The history as it was before any sync, once; never overwritten."""
        base, _ = os.path.splitext(os.path.abspath(self.history.file_path))
        target = base + self.BACKUP_SUFFIX
        if os.path.exists(target):
            return
        partial = target + '.tmp'
        try:
            if os.path.exists(partial):
                os.remove(partial)
            self.history.BackupTo(partial)
            os.replace(partial, target)
        except Exception as exc:
            raise SyncFailed(f'No sync without a backup first: {exc}') from exc
        Log.Info(CATEGORY_NAME, f'Nexus sync: history backed up to {target}')

    def _prune_conflicts(self, now: float|None=None) -> int:
        """Remove kept-aside conflict texts older than CONFLICTS_KEEP_DAYS."""
        directory = self._path(self.CONFLICTS_FOLDER)
        if not os.path.isdir(directory):
            return 0
        cutoff = (now if now is not None else time.time()) - self.CONFLICTS_KEEP_DAYS * 86400
        removed = 0
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if not name.endswith('.json') or not os.path.isfile(path):
                continue
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed += 1
            except OSError:
                continue
        if removed:
            Log.Info(CATEGORY_NAME, f'Nexus sync: removed {removed} conflict copies older than {self.CONFLICTS_KEEP_DAYS} days')
        return removed

    def _keep_aside(self, folder: str, key: str, tag: str, text: str) -> str:
        """A game's text kept where nothing reads it, for recovery by hand."""
        directory = self._path(folder)
        os.makedirs(directory, exist_ok=True)
        stem = re.sub(r'[^A-Za-z0-9._-]+', '_', key)
        stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime())
        path = os.path.join(directory, f'{stem}.{tag}-{stamp}.json')
        count = 1
        while os.path.exists(path):
            count += 1
            path = os.path.join(directory, f'{stem}.{tag}-{stamp}-{count}.json')
        self._write(path, text)
        return path

    @staticmethod
    def _write(path: str, text: str) -> None:
        partial = path + '.tmp'
        with open(partial, 'w', encoding='utf-8') as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(partial, path)

    @staticmethod
    def _read_json(path: str) -> Any:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (OSError, ValueError):
            return None

    def _load_state(self) -> None:
        saved = self._read_json(self._path(self.STATE_FILE))
        state: Dict[str, Any] = saved if isinstance(saved, dict) else {}
        if not str(state.get('device', '')):
            state['device'] = secrets.token_hex(16)
        if not isinstance(state.get('synced'), dict):
            state['synced'] = {}
        state['hlc'] = int(state.get('hlc', 0))
        state['cursor'] = int(state.get('cursor', 0))
        state['server_id'] = str(state.get('server_id', ''))
        state['first_done'] = bool(state.get('first_done', False))
        self._state = state
        queued = self._read_json(self._path(self.OUTBOX_FILE))
        self._outbox = queued if isinstance(queued, dict) else {}

    def _save_state(self) -> None:
        os.makedirs(self.state_folder, exist_ok=True)
        self._write(self._path(self.OUTBOX_FILE), json.dumps(self._outbox))
        self._write(self._path(self.STATE_FILE), json.dumps(self._state))

    def DeviceId(self) -> str:
        if not self._state:
            self._load_state()
            self._save_state()
        return str(self._state['device'])

    ############################################################################
    # HTTP

    def _call(self, method: str, path: str, body: Any=None) -> Dict[str, Any]:
        data = None if body is None else json.dumps(body).encode('utf-8')
        request = urllib.request.Request(
            self.base_url() + path, data=data, method=method,
            headers={
                'Authorization': 'Bearer ' + self.secret,
                'Content-Type': 'application/json',
            },
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            with exc:
                if exc.code == 401:
                    raise SyncFailed('The sync server refused the secret.') from exc
                try:
                    detail = json.loads(exc.read().decode('utf-8')).get('error', '')
                except Exception:
                    detail = ''
            raise SyncFailed(
                f'The sync server answered {exc.code}' + (f': {detail}' if detail else '') + '.'
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise SyncFailed(
                f"The sync server at {self.address} can't be reached; "
                'games wait here until it can.'
            ) from exc
        try:
            reply = json.loads(raw.decode('utf-8'))
        except ValueError as exc:
            raise SyncFailed('The sync server sent something unreadable.') from exc
        if not isinstance(reply, dict):
            raise SyncFailed('The sync server sent something unreadable.')
        return reply
