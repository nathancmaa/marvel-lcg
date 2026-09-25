# Handoff: working on Cerebro

Written 2026-09-25 at the close of a long working session, for whoever picks
this fork up next, human or agent. It records how the work is actually done
here, which is not always what the older docs say. Where this file and
`AGENTS.md` disagree, this file reflects Nathan's current instructions.

## Where things stand

- **Version 0.7.13.2**, released 2026-09-17. `master` is clean and pushed,
  tags `v0.7.13`, `v0.7.13.1` and `v0.7.13.2` are on GitHub. Nothing has
  landed since. Nathan reports the build as stable.
- **Every scenario and every hero launches.** All 124 scenario files
  (standard and expert) reach the mulligan, and each of the 69 starter heroes
  has launched at least once. `tools/launch_sweep.py` checks this in about a
  minute; see Methodology.
- **Every card script builds its abilities.**
  `unit_test/test_every_card_builds_abilities.py` builds all of them in a few
  seconds. It exists because an assertion raised while building a card's
  abilities kills the whole server, and Enchantress could not be started
  until it was found.

## Who plays, and how

- Nathan plays **true solo**: one hero against the villain, sometimes
  two-handed (two heroes, one person, hot seat). Undo speed and multiplayer
  are low priority.
- Play happens on an **iPad in Firefox**, over a Cloudflare tunnel at
  `mc.nathanma.net`, against a server on the NAS. iPad Firefox cannot share
  files and cancels downloads a page starts on its own; anything that needs
  a user gesture on iOS must hang off a real tap.
- Game results go to **BG Stats** through its deep link, one play at a time.

## Build priorities

From `FORK-GOALS.md` and standing instructions, in order:

1. **Rules correctness** under Rules Reference 1.8, the only supported rules
   model. Old replays that are not `v18_all` fail early by design.
2. **Reliable saves, undo, redo and Continue.** Most of the September
   bug reports were here; see the replay notes below before touching it.
3. **Starting a game is easy.** Quick Game, deck pickers, remembered choices.
4. **UI that holds up on a tablet for a whole session.** Touch targets,
   legibility, keyboard shortcuts that mirror the buttons.
5. **Results leave the app.** Game history, BG Stats, Marvel Champions
   Tracker export.

Do not re-propose these; each was considered and declined:

- An engine rewrite, or undo performance work. Evaluated and scrapped
  2026-09-07; a rewrite was estimated at years, and solo undo is fast enough.
- PvP or broad four-player work. No PvP code exists in this fork.
- A BG Stats file export. A `.bgsplay` batch never imported on the iPad and
  was removed at Nathan's request. The deep link is the integration.

## Methodology

### The finishing routine

A change is done when it is tested, committed on `master`, and pushed.
Nathan deploys by pulling from GitHub, so a local commit is invisible and
undeployable. This overrides the "do not commit or push" line in `AGENTS.md`.

1. **Full suite.** Run every test module except `test_task` (it bumps
   versions and makes commits) and `test_all` (needs a gitignored
   `launch-debug.json`):

   ```bash
   ./.venv/Scripts/python.exe -m unittest $(ls unit_test/test_*.py | sed 's|/|.|;s|\.py||' | grep -vE '\.(test_all|test_task)$' | tr '\n' ' ')
   ```

   On Windows, eight failures are the known baseline and pass on Linux:

   | Module | Count | Cause |
   |---|---|---|
   | `test_persistent_save_paths` | 3 | backslash path separators |
   | `test_asset_versioning` | 2 | CRLF line endings |
   | `test_fear_no_evil_*` | 3 | a Windows-only mock format error |

   Anything beyond those eight is real. The last run was 868 tests.

2. **TypeScript** after any frontend change. The emitted `.js` is gitignored
   and the Docker build compiles it itself, but compile locally to catch type
   errors and to run the dev server:

   ```bash
   cd public/js && npx --yes --package=typescript tsc -p tsconfig.json
   ```

3. **Commit and push to `master`.** Titles are a plain sentence saying what
   the change does for a player ("Let The Hood pick a modular set"). The body
   says what was wrong, why, and what now happens. End with the
   `Co-Authored-By` trailer for the model in use.

### Releases and version numbers

- **Bump conservatively.** BUILD for fixes and polish, PATCH for new
  capability. MINOR is not for a big week; Nathan has corrected over-large
  bumps three times, and the 0.8 line is not available. When Nathan says
  "minor" it means a small bump, not the MINOR field.
- **Four things move together**, and tests guard them: `build.py`
  (`PATCH`, `BUILD`), the version div in `public/main.html`, the
  `> Current release version:` banner in `CHANGELOG.md`, and a new changelog
  entry. By convention the banner and start page show `MAJOR.MINOR.PATCH`
  only, so a BUILD release leaves those two unchanged.
- **Changelog style:** a one-line summary under the heading, then bullets
  that open with a bold phrase and explain the change in plain prose from
  the player's side. Look at the 0.7.13 entries.
- **Tag and push:** an annotated tag named `vX.Y.Z`, or `vX.Y.Z.B` when
  BUILD is not zero, with the message `Version X.Y.Z.B`. Then
  `git push origin master --tags`. The release commit is titled
  `Release X.Y.Z.B`.
- **Releases have lagged before.** 0.7.13 and 0.7.13.1 were cut in arrears,
  and the changelog intro records it. When a batch has been played and
  reported stable, offer a release.

### Local dev server

- Start it with the Browser pane launcher (`preview_start` name
  `marvel-lcg`, port 2345), configured in `.claude/launch.json`. Restart it
  after any Python or compiled-JS change; asset URLs are fixed at startup.
- Every page and JSON route is gated on a cookie `app_version` set to
  `MAJOR.MINOR.PATCH.BUILD` plus `r`, currently `0.7.13.2r`. Visit
  `clean_cache.html` in the browser, or pass `-b "app_version=0.7.13.2r"` to
  curl.
- The Browser pane is usually hidden. Screenshots time out, ResizeObserver
  never fires, and animation frames stall. Verify through DOM queries.
- The dev history database is `statistics.sqlite3` in the repo root. Seed it
  with `GameHistory(); h.Initialize(); h._store_game({...})`.

### Launching games without a browser

`tools/launch_sweep.py` is a scripted table client. It opens the websocket,
acknowledges every render, and starts games through `/new`, so a scenario
launches in half a second. Use it after any change to setup, card
construction, scenario data or a card factory:

```bash
./.venv/Scripts/python.exe tools/launch_sweep.py            # all scenarios
./.venv/Scripts/python.exe tools/launch_sweep.py the_hood   # a subset
```

The same protocol drives a game past setup: read `/get_ask?p=0`, answer by
POSTing `{"id": N, "targets": [...], "resources": [...]}` to `/post?p=0`.

### Reproducing a reported bug

- **Nathan's saves** are the fastest path. Quick saves are JSON recordings;
  drop one in the repo root and load it through the debug route:

  ```bash
  curl -b "app_version=0.7.13.2r" "http://127.0.0.1:2345/debug?/load%20save_1.json:-1"
  ```

  Other debug commands include `/undo auto`, `/skip 0` (redo) and `/resign`.
  Saves that once broke are kept as fixtures in `unit_test/fixtures/saves/`
  and replayed whole by `unit_test/test_saved_games_replay.py`.
- **A hung engine** shows where it waits with py-spy, installed in the venv:

  ```bash
  ./.venv/Scripts/py-spy.exe dump --pid <server pid>
  ```

- **Rules questions:** read the printed card, not only the text. MarvelCDB's
  API text sometimes drops a line; Taunting Presence's "Threat cannot be
  removed from Light at the End" is missing there. The scan is at
  `https://marvelcdb.com/bundles/cards/<code>.png`. Before calling something
  a bug, check whether an encounter card explains it. Life-Size Decoy
  ("the engaged player cannot thwart side schemes") looked exactly like a
  targeting bug.

### Validating card changes

`CardsDB` swallows import errors, so a server that starts proves nothing
about a card script. Run `test_every_card_builds_abilities` for structure,
then a focused test or a launched game for behaviour. Structure and rules
are separate checks.

### Editing on Windows

Bash heredocs with backticks or backslash line continuations often fail
here. For multi-line patches, write a small Python script to a scratch file
and run it, and anchor replacements on text without continuation
backslashes.

## Deployment

- **Host:** a UGREEN DXP4800 NAS (Pentium Gold 8505, 32 GB). The checkout is
  `/volume1/docker/marvelchampions`. Runtime data lives outside it under
  `/volume1/docker/marvel-lcg/`: `runtime` (history database, saves,
  campaign progress, active session), `assets`, `replays`, and both deck
  folders.
- **Deploy from the NAS terminal, never the Container Manager UI:**

  ```bash
  cd /volume1/docker/marvelchampions && git pull && docker compose up -d --build
  ```

  The UI ignores `docker-compose.override.yaml`. Without it the container
  comes up named `marvel-lcg` instead of `marvelchampions`, the bind mounts
  fall back to relative paths, and history, collection and decks all appear
  to be gone. Nothing is deleted; a terminal redeploy restores it. If Nathan
  reports missing data after a deploy, check the container name first.
- **The override** is gitignored and holds the absolute NAS paths,
  `container_name: marvelchampions` and `network_mode: host`.
  `docker-compose.override.yaml.example` shows its shape, and `.env` sets
  `COMPOSE_PROJECT_NAME=marvelchampions`.
- **Logs need sudo.** Without it the permission error is silently hidden by
  a grep:

  ```bash
  sudo docker logs --tail 400 marvelchampions 2>&1 | grep -aE "Error|Traceback"
  ```

- **After a deploy**, JSON routes carry ETags, so decks and scenarios
  refresh on the next load. If a page still looks stale on the iPad, a hard
  refresh fixes it.
- `INSTALL-SERVER.md` describes a systemd install under `/opt/marvel-lcg`.
  That is not how this deployment runs.

## Architecture notes earned the hard way

- **Undo and replay** re-run the recorded inputs from the start; there are no
  state snapshots. `engine/controller/module/replay.py` holds the recording.
  Never edit the recording while it is being replayed: a replayed choice has
  a fresh effect number, and cutting the recording on that difference is
  what made loads stop early and undo jump turns. Choices are compared
  without their effect number. A recorded choice that no longer fits the ask
  is dropped and the ask is put again, rather than asserted on.
- **Randomness** goes through `engine/lib/random.py` with the game seed.
  `RandomChoice` draws an index so lists of tuples work and seeds stay
  stable.
- **An assertion while building a card's abilities** is fatal to the server
  process, which exits with code 0. It happens during scenario setup, so it
  looks like one scenario failing to start.
- **Game history** keys a live game on its game id, which an undo keeps. A
  game that ends a second time after an undo now replaces its earlier
  result. Replay imports and physical games are never overwritten this way.
- **The villain-beaten stripe** on a Quick Game tile is the selected hero's
  record, not the villain's overall one. Two-handed, it splits per seat.
- **Rendering is lockstep:** the engine waits for the browser to draw and
  acknowledge every frame. That wait, not the engine, dominates late-game
  latency.

## Open threads

- **Branch `perf/render-sync`** is unmerged: one commit, now 62 behind
  `master`. It lets the browser pace renders instead of the engine and cut a
  measured late-game villain phase from 27.8 s to 15.1 s. Nathan has not
  asked for it; it needs a rebase and testing on the iPad before it could
  ship.
- **Branch `chore/nas-setup-and-decklist-fix`** is fully merged and can be
  deleted.
- **NEW badges.** Content in the game but not yet played through wears NEW
  on its Quick Game tile. The lists are near the top of
  `public/js/solo.ts`: Kingpin and the Fear No Evil scenarios, She-Hulk,
  Vision, the five underlings, and the Echo, Daredevil, Jessica Jones and
  Luke Cage heroes. Take an id out once Nathan has had a real game with it.
- **Stale docs.** `AGENTS.md` and `INSTALL-SERVER.md` still say 0.7.4 and
  describe systemd. `AGENTS.md` also says not to commit or push, which Nathan
  has overridden.

## Memory

Claude Code sessions in this project load notes from
`C:\Users\natha\.claude\projects\C--Users-natha-code-marvel-lcg\memory\`.
They cover the version rule, the deploy trap, BG Stats behaviour, latency
measurements, the declined rewrite and dev-server quirks. They overlap with
this file on purpose; keep both current.
