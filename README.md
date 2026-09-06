# Marvel Champions Digital: Ronin Edition

> Version 0.8.1 — “Archive”

> **This edition uses Marvel Champions Rules Reference v1.8 as its supported rules model.**

> [!CAUTION]
> **Please support the physical game.** Buy Marvel Champions and its expansions from Fantasy Flight Games, and support your friendly local game store whenever possible. Ronin Edition is intended as a testing, training, and learning platform—a convenient way to explore heroes, practise decks, and become familiar with the game—not as a replacement for the physical card game.

## New in 0.8.1

Building the deck you take in, and choosing how hard the game pushes back.

- **Prebuilt aspect decks.** 25 aspect-and-basic card lists, pairable with any
  hero. A deck on MarvelCDB is always attached to one hero, so a good aspect
  list could not be lifted off it and handed to somebody else; these carry the
  cards alone. Pick a hero and a list from the two dropdowns and the hero keeps
  its identity, signature cards, obligation and nemesis set. Lists and notes
  come from a BoardGameGeek geeklist, credited in the picker.
- **Standard I, II or III.** Every game used to be dealt Standard I. All three
  sets were already implemented; only the choice was missing. Standard II and
  III stand in for Standard I rather than stacking on it, Expert still layers
  on top, and the two scenarios played without a Standard set — Kingpin and
  The Wrecking Crew — say so instead of being given one.
- **Deck titles link to MarvelCDB.** The title in the Hero heading is the way
  back to a deck's own page, for a synced deck picked off a tile as much as
  one pasted in, and for the chosen aspect deck. Only decks this app fetched
  are linked: a precon's own metadata link is not a deck page.
- **"My Decks" instead of "Precon".** That tab lists every synced deck
  alongside the starters, and had been named after only half of what is in it.

## Previously in 0.8.0: Archive

Finding what you want to play, and knowing what you own.

- **Scenario filtering.** The Quick Game scenario picker gained the same
  controls as the hero picker: filter to one box, sort by new content,
  release order or name, and group by box — with boxes listed in the order
  they came out.
- **Heroes that share a name are told apart.** Black Panther is both T'Challa
  and Shuri; Spider-Man is both Peter Parker and Miles Morales. Each pair used
  to collapse into a single entry.
- **Collection comparison.** The Deck Viewer shows which cards in a deck come
  from products you have not marked as owned in Collection & Stats — for
  moving between the digital and physical games. Hidden until you record a
  collection; every card stays playable here either way.

## Previously in 0.7.0: Ronin

The first release of this fork, continuing from
[z00lus/marvel-lcg](https://github.com/z00lus/marvel-lcg) 0.6.1. No rules or
card behaviour changed; this release is about finding your decks and seeing
the board.

- **Deck browsing.** Filter the Quick Game hero picker to one hero, sort by
  deck name, hero, aspect, or most recently updated, group by hero, and hide
  precon decks. The Deck Viewer gets the same grouping and precon toggles, and
  links each synced deck back to its MarvelCDB page.
- **Correct MarvelCDB syncing.** A bare deck number now resolves to a
  published decklist rather than a personally shared deck. The two are
  separate records that share their numbering, so a number copied off the site
  could previously sync something else entirely.
- **A board that fits the screen.** Displays wider than 16:9 are no longer
  letterboxed — a 3440x1440 screen gains roughly five card widths per row —
  and rows no longer slide underneath the deck columns as upgrades pile up.
- **Prompts that stay out of the way.** The target-selection prompt moves off
  the cards it is asking you to choose between, and the right-hand button bar
  keeps a strip on screen you can actually hit.
- **Decks that survive a rebuild.** User decks are stored outside the
  container, so a `docker compose up --build` no longer discards everything
  synced from MarvelCDB.

**0.7.1** fixed The Elephant's Trunk, which could not be used at all, and
reports decks that name cards this build does not implement when they sync
rather than when you draw them. See the [changelog](CHANGELOG.md) for detail.

## Previously in 0.6.1: Fear No Evil

The complete solo Quick Game scenario line from **Fear No Evil** is now
available: five interchangeable-underling scenarios plus the fixed Kingpin
finale.

- **Stop the Presses!** in Standard and Expert modes, with deterministic
  Daily Bugle Persona setup, all four stamina-powered Persona supports, and
  the required **Tombstone** and **Tracksuit Mafia** modular sets.
- **Protection Racket** in Standard and Expert modes, with all five selectable
  main schemes and the **Disasters** and **Tracksuit Mafia** modular sets.
- **The Getaway** scenario in Standard and Expert modes.
- **Art Museum Heist** in Standard and Expert modes, including its ART
  attachment flow and the required **The Owl** encounter set.
- **The Raft Breakout** in Standard and Expert modes, including **Master Key**,
  PRISONER setup, the required **Tombstone** encounter set, and all currently
  implemented underling choices.
- **Kingpin** in Standard and Expert modes, including his two-sided villain
  stages, nemesis/UNDERLING setup, Public Support, and the required
  **Tombstone** and **Tracksuit Mafia** sets without the Standard set.
- **Bullseye**, **Electro**, **Hammerhead**, **Purple Man**, and **Typhoid
  Mary** as selectable underlings, each with Standard and Expert stage pairs
  and a complete encounter set. Typhoid Mary includes her two-sided villain,
  Disturbed Psyche, and Mary Walker/Establish Trust state cycle.
- The required **Cops** and **Drive** encounter sets.
- **Echo** and **Daredevil** starter decks and hero integrations.
- Clear `NEW` labels for the new scenarios, heroes, and underlings in Quick
  Game, with new scenarios shown first and the correct main-scheme previews.

All scenario scripts and setup paths have focused automated coverage. Manual
solo replay validation remains ongoing for the newly completed encounters.

Other additions in this release include:

- **Jessica Jones**, her starter deck, nemesis set, and focused rules tests.
  Cards whose published art is unavailable are rendered as readable text-only
  cards instead of blank placeholders.
- An optional **1–5 star rating** for both the hero and scenario at the end of
  a game. Ratings are stored with the shared game history for future rankings.

## Fork Goals

This fork focuses on a simple and convenient **solo Marvel Champions experience**.

- **Solo-first gameplay:** the primary use case is one player controlling one hero. Multiplayer and PvP are not development priorities.
- **Simplified UI:** starting a game should require only choosing a scenario, selecting a prepared hero deck, and pressing **Play**. Campaigns use a separate, equally simple flow.
- **Linux server:** the game is designed to run as a lightweight self-hosted server on Linux, with play happening from a desktop, tablet, or mobile browser over a trusted local network.

Development should prioritize rules correctness, reliable saves and replays, and improvements that make solo games easier to start and play.

## Snapshot

![](/docs/assets/image-6.png)

## Running

### Linux and macOS

Install Git, Python 3.10 or newer, and Node.js, then run:

```bash
INSTALL_DIR=marvel-lcg   # any folder name you like
git clone https://github.com/nathancmaa/marvel-lcg.git "$INSTALL_DIR"
cd "$INSTALL_DIR"
./run.sh
```

Git names the folder after the repository when no destination is given, so
set `INSTALL_DIR` if you would rather keep several versions side by side.

`run.sh` creates the virtual environment, installs Python dependencies, compiles the frontend when necessary, and starts the server. Open `http://127.0.0.1:2345/` locally or `http://SERVER_IP:2345/` from another device on the same trusted network.

### Docker

From the cloned project directory, run:

```bash
docker compose up --build
```

Open `http://127.0.0.1:2345/`. Use `docker compose up --build -d` to run in the background and `docker compose stop` to stop it. Docker is also the recommended way to run the server on Windows.

The `runtime/` bind mount preserves statistics, campaign progress, the active **Continue Game** checkpoint, and QSave/Save 1–3 files across container rebuilds. Saved replays and downloaded assets are likewise preserved by their respective bind mounts.

### Headless AI player

The repository includes a Codex skill and MCP server that can play and test
solo games directly through the engine without a browser or WebSocket client.
Codex discovers the repository-scoped `marvel-lcg-player` skill automatically
when opened in this repository. Register its MCP server once with:

```bash
python3 tools/install_marvel_lcg_codex.py
```

For a game server running on another machine on the same trusted network:

```bash
python3 tools/install_marvel_lcg_codex.py \
  --server-url http://SERVER_IP:2345
```

Restart Codex after registration, start the game server, and invoke
`$marvel-lcg-player` or ask Codex to play or test a solo game. See
[Headless MCP player](docs/headless_mcp.md) for the tool contract, behavior,
and safety notes.

### Collection and tabletop games

Open **Collection & Stats** from the main menu to mark the physical products you own, review digital and tabletop win rates, and track achievements. Use **Log Physical Game** to add a finished physical solo game. Manually logged games can be edited or deleted; statistics and achievement progress are recalculated automatically. All of this data is stored in the same `statistics.sqlite3` database used by digital game history.

#### Stopping and starting the Docker server

Temporarily stop the server while keeping its container:

```powershell
docker compose stop
```

Start the same container again without rebuilding it:

```powershell
docker compose start
```

Restart the running server:

```powershell
docker compose restart
```

`docker compose down` may also be used when you want to stop and remove the container and its Compose network. The next `docker compose up -d` recreates them. Project data remains in the `runtime/`, `replays/`, and `assets/` bind-mounted host directories. Running `down` is not required for a normal update, and `down -v` should be reserved for cases where Docker-managed volumes are intentionally being removed.

#### Updating on Windows with Docker Desktop

Open PowerShell in the existing cloned repository, update the source, and rebuild the service:

```powershell
git status --short
git pull --ff-only origin master
docker compose build --pull
docker compose up -d --remove-orphans
```

Continue Game is stored in `runtime/save_active_session.json`; QSave and Save 1–3 are stored in `runtime/save_0.json` through `runtime/save_3.json`. Because `runtime/` is mounted from the Windows host, these files survive container rebuilds and recreation.

If `git status` shows tracked local changes, preserve or commit them before pulling. Do not reset them blindly. Check the updated container with:

```powershell
docker compose ps
docker compose logs --tail=100 marvel-lcg
```

Open `http://127.0.0.1:2345/` and use `Ctrl+F5` if the browser still shows cached frontend files. Future updates only require `git pull --ff-only origin master`, `docker compose build --pull`, and `docker compose up -d --remove-orphans`. The `down -v` option is unnecessary for updates and should be used only when Docker-managed volumes are intentionally being removed.

## Progress

### Compared with upstream

Compared with the original [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg), this fork currently adds:

- A Rules Reference **v1.8** engine update focused on solo rules correctness, including timing, status cards, damage, targeting, and ability initiation.
- Solo-first **Quick Game** and **Campaign** screens with prepared-deck selection, remembered choices, and optional Expert difficulty.
- A cohesive Ronin-themed interface with improved tablet and touch layouts, a settings screen, adjustable animation speed, and replay autosaving.
- Reliable replay saving, browsing, downloading, loading, step controls, timeline seeking, and paused-at-start playback.
- Unified SQLite history for digital, imported-replay, and manually logged physical games, with collection management, source filters, matchup statistics, and shared achievements.
- Optional post-game hero and scenario ratings stored alongside the shared game history.
- Manual and daily synchronization of public MarvelCDB deck IDs into a clearly marked user-deck collection.
- Readable text-only card rendering when a card is implemented but published art is unavailable.
- Better self-hosting through `run.sh`, Docker Compose, LAN-friendly defaults, a systemd unit, and Linux server documentation.

### Community integrations and new heroes

Campaign support and the initial Hercules implementation were merged from the [sdolle1775 fork](https://github.com/sdolle1775/marvel-lcg). The merged campaign work covers Mutant Genesis, NeXt Evolution, Age of Apocalypse, Agents of S.H.I.E.L.D., Galaxy's Most Wanted, and The Mad Titan's Shadow, together with related campaign-state fixes. After the merge, Hercules' special decks, card scripts, UI placement, and rules behavior were corrected in this fork and covered by focused tests.

The **Echo**, **Wonder Man**, **Daredevil**, and **Jessica Jones** hero integrations are original work created for this fork. They include starter decks, card scripts, special-deck handling where required, targeted tests, and ongoing replay-based playtesting.

Fear No Evil integration includes **Stop the Presses!**, **Protection
Racket**, **The Getaway**, **Art Museum Heist**, **The Raft Breakout**, and the
fixed **Kingpin** finale; all five selectable underlings (**Bullseye**,
**Electro**, **Hammerhead**, **Purple Man**, and **Typhoid Mary**); and the
**Cops**, **Drive**, **The Owl**, **Tombstone**, **Disasters**, and **Tracksuit
Mafia** encounter sets. Standard and Expert setup, card loading, and focused
rules behavior are covered by automated tests; manual replay playtesting of
the newest encounters is ongoing.

Based on the original open-source [Marvel Champions: Digital Edition](https://irefrixs.itch.io/marvel-lcg) by Irefrixs.

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。
