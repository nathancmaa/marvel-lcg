# Nexus sync of the game history

Cerebro is one client of the Nexus sync server, the small LAN service that
keeps Nexus's play data (Phoenix for Marvel Champions, Dunwich for Arkham)
the same on every device. The server and its protocol belong to
`marvel-lcg-phoenix` (`server/nexus_sync/`, `docs/nexus-sync.md` there). Cerebro
syncs only Marvel Champions games. The code is `game/statistics/nexus_sync.py`,
which mirrors Nexus's own client, `godot/scripts/nexus_sync.gd`.

A game played in Cerebro's browser UI reaches every Nexus device, and their
games appear in Cerebro's history and count for its achievements.

## Switching it on

| Setting | Environment | Command line / `launch.json` |
|---|---|---|
| Server address, `IP:port` | `NEXUS_SYNC_ADDRESS` | `-nexus_sync_address` / `nexus_sync_address` |
| Shared secret | `NEXUS_SYNC_SECRET` | `-nexus_sync_secret` / `nexus_sync_secret` |

The command line and `launch.json` override the environment. Pass the secret
through the environment: a command line is visible to every user on the
machine. **If either setting is empty, sync does nothing at all:** it starts no
thread, writes no files, and makes no requests.

`docker-compose.nas.yaml` passes both through as `${NEXUS_SYNC_ADDRESS-}` and
`${NEXUS_SYNC_SECRET-}`. Set them in the Portainer stack's environment, or in a
`.env` file beside the compose file, and redeploy.

## What it syncs

Each game is one record, `mc/game/<source_key>`. Its body is the game's row
as canonical JSON: the `games` columns Phoenix knows (`SYNC_COLUMNS`), plus
`players`, `card_statistics` and Phoenix's optional `performance`, with
sorted keys and no spaces. `GameHistory.SyncRows()` produces it. The text is
byte-for-byte what Phoenix's `History::sync_rows` and its
`tools/sync_import_phoenix.py` produce for the same row. This matters because
a game whose text differed between devices would be sent again on every sync.
`tests/test_nexus_sync.py` checks this against the import tool.

- Cerebro's `imported_from_replay`, `replay_analysis_status` and
  `replay_analysis_error` are not synced. Phoenix has no such columns. A game
  pulled over one held here keeps its own values for them.
- Phoenix's `performance` detail lives in a `phoenix_performance` table. That
  table is part of schema 8 as Phoenix defines it, so the migration creates it
  without raising the version: Phoenix refuses a history newer than it knows.
- A pulled row is written the way Phoenix's `apply_sync` writes it. A null
  column takes the table's default, and seats, card statistics and
  performance are replaced. A replaced game keeps its database id, so its
  achievement links survive. Afterwards the achievements are recalculated
  (`AchievementEvaluator.Recalculate`). Unlocks are permanent: a pulled game
  can add achievements but never removes one.

Decks (`mc/deck/<file>`) are not synced. Nexus syncs a deck file's text
as-is, but Cerebro's decks are a different JSON shape, so this would need a
converter each way. The converter would map hero identity code to the hero
deck and the player deck card list with counts, aspect, name and source. The
same deck would also have to round-trip to identical text, or it would be
re-sent on every sync.

## When it runs

A background thread, never the game loop, runs it:

- at startup;
- when a played game is recorded (`GameHistory.on_change`, called from
  `RecordCompletedGame`);
- every 5 minutes;
- after a failure, again at 30 s, 1, 2 and 5 minutes, then every 5 minutes.

Each run scans the history and compares each game's SHA-256 with the hash
last synced. It puts what changed, appeared or disappeared in the outbox,
stamped with a hybrid logical clock. It pushes the outbox, then pulls the
other devices' changes from its cursor, a page at a time. The scan runs even
when the server can't be reached, so a game played while it is away is
stamped when it is played and waits in the outbox.

If more than 3 games, and more than a tenth of them, go missing at once, the
history is treated as damaged rather than edited. No deletions are sent and
the games are pulled back.

If the server's id changes (a new or restored server), Cerebro forgets its
cursor and sends everything it holds again, with the stamps it had.

## Protecting Cerebro's own history

Many of Cerebro's games exist nowhere else, so:

1. **Backup first.** Before the first sync it ever makes, Cerebro takes an
   SQLite online backup of the history beside it, `statistics.pre-nexus-sync.sqlite3`.
   It never overwrites that file. If the backup fails, the sync doesn't run.
2. **The first sync pulls before it queues.** Nexus's client queues every
   local game as new on its first sync, which would let Cerebro's copy
   replace whatever the server holds. Cerebro instead pulls everything first
   and compares:
   - Same text: the game is marked synced and nothing is sent.
   - Different text on a `phoenix:` key (Phoenix's games): the server's
     version is taken. The text held here is saved to `sync-conflicts/` first.
   - Different text on any other key (`game:`, `mct:`, `physical:` table
     games, ...: Cerebro's own games): Cerebro's text wins. It is sent with a fresh stamp, which beats
     everything pulled, and the server's text is saved to `sync-conflicts/`.
     This also applies when the server holds a deletion of that game.

   After the first sync, the newest stamp wins, as on every Nexus device.
3. **Nothing is removed without a copy.** Before a pulled version replaces a
   game held here, the game's current text goes to `sync-conflicts/`. Before
   a pulled deletion removes one, it goes to `sync-trash/`. The server also
   keeps every version anyone sent (`GET /v1/revisions?id=mc/game/<key>`).

## Files

All of these sit beside the history database (`runtime/` on the NAS):

| File | Holds |
|---|---|
| `nexus-sync-state.json` | device id, clock, cursor, server id, hash and version last synced per game |
| `nexus-sync-outbox.json` | stamped changes waiting to be sent |
| `sync-conflicts/<key>.here-<time>.json` | a local text replaced by a pulled one |
| `sync-conflicts/<key>.from-<device>-<stamp>.json` | a server text Cerebro's own game outranked on the first sync |
| `sync-trash/<key>.deleted-<time>.json` | a game removed by a pulled deletion (kept indefinitely) |

Files in `sync-conflicts/` older than 30 days are removed at the start of each
sync; the server keeps every version (`/v1/revisions`) for recovery after that.
| `statistics.pre-nexus-sync.sqlite3` | the one-time backup |

To restore a game from one of these, read its text with `json.loads`, then
pass it to `GameHistory.ApplySync([row], [])`.

## Tests

```bash
.venv/bin/python -m unittest tests.test_nexus_sync
```

These start the real Nexus server in-process from a `marvel-lcg-phoenix`
reference checkout: `../nexus-sync-ref` beside this repository, or the path in
`NEXUS_SYNC_REF`. Without that checkout they are skipped.
