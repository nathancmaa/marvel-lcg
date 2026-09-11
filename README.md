# Marvel Champions Digital: Cerebro

A self-hosted, solo-first digital table for **Marvel Champions: The Card Game**.
It runs as a Docker container on a home server and you play it from a browser —
desktop, tablet or phone — anywhere on your own network.

> [!CAUTION]
> **Please buy the physical game.** Marvel Champions is designed and published
> by **Fantasy Flight Games**; the cards, characters and artwork are theirs, and
> Marvel's. This project is not affiliated with either, sells nothing, and
> ships no card art — it downloads what it displays on demand and works best
> for people who already own the products they are playing.
>
> Treat it as a practice table: a place to learn a hero, test a deck before
> sleeving it, or get a game in when the box is not in front of you. It is not a
> substitute for owning the game, and it is not built to be one. Buy the boxes
> from FFG, and buy them from your local game store if you have one.

![The table, mid-game](docs/assets/image-6.png)

## Where this came from

Three people's work, in order:

1. **[irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg)** — the
   original Marvel Champions: Digital Edition. The rules engine, the card
   scripting system and the table itself are theirs; everything below is built
   on top of it.
2. **[z00lus/marvel-lcg](https://github.com/z00lus/marvel-lcg)** — the Ronin
   Edition fork, which brought the solo-first framing, the v1.8 rules pass, the
   replay system and the first serious self-hosting story. Versions 0.6.x are
   theirs.
3. **This fork** — 0.7.x onwards. What follows is what it is for.

If you are choosing where to start, start upstream. This fork exists because I
wanted specific things for my own solo play, not because the ones above needed
fixing.

## What this fork is for

A single-player table that keeps a record, on a server I control.

- **A Docker package that runs on a server.** One container, five bind mounts,
  no database to administer. It lives on a NAS and every device in the house
  plays the same games against the same history over the local network. There is
  no cloud service, no account, and nothing leaves the machine.
- **UI and accessibility that survive a long session.** Legibility, touch
  targets, contrast and keyboard reach are treated as features. Includes proper
  **ultrawide and 2/3-width layouts** — the board reflows rather than stretching,
  and side schemes stop colliding with minions at awkward widths.
- **Standing answers.** Tick a card that carries an optional Response or
  Interrupt and the game stops asking about it — it answers for itself when the
  window comes round. The **Priority** panel lists what you have ticked and the
  order it fires in, which is what settles it when two of them trigger at once.
  The list belongs to the game being played and is cleared when a new one
  starts. A tick only ever answers a question the game asked: it never acts for
  you, and an unticked card still prompts every time.
- **Playable from the keyboard.** OK, cancel and undo each take a key of your
  choosing beside Enter, Escape and ctrl+z; when the game offers a choice, the
  home row takes the options in the order they are shown, with each key drawn
  on its own button. All remappable in Settings, where a key you choose beats
  whatever the table did with it by default.
- **Stat tracking worth looking at.** One SQLite history covering digital games,
  imported replays and games played at the table, with a **hero × scenario
  coverage grid** showing the hardest difficulty each pairing has been beaten
  at. Games move in and out: import a **Marvel Champions Tracker** export, push
  a finished play to **BG Stats**.
- **Universal aspect decks.** Pick a hero, pick a prebuilt aspect deck, play —
  the community's Universal Prebuilt Decks, wired into both Quick Game and
  Campaign.
- **A deck tracker and mulligan helper** *(in testing)*. What is left in the
  deck mid-game, and what to look for in an opening hand — quoting the deck
  author's own advice from MarvelCDB where they gave any, and ranking the deck
  where they did not.
- **Deck building against what you actually own.** Mark your collection, and the
  deck viewer will tell you which cards in a netdeck you are missing and suggest
  ones you own instead.
- **Difficulty that goes past Expert.** Standard I/II/III, Expert, and **Heroic
  1–4**, all selectable from Quick Game and all recorded.
- **Proxy printing** for cards you do not own yet, laid out for a home printer.
- **MarvelCDB syncing.** Paste deck IDs once; they refresh daily.

Rules correctness, reliable saves and replays, and getting into a game quickly
come before anything else here.

## Running it

Docker is the intended way to run this. Everything else is a development
convenience.

```bash
git clone https://github.com/nathancmaa/marvel-lcg.git
cd marvel-lcg
docker compose up -d --build
```

Open `http://127.0.0.1:2345/`, or `http://SERVER_IP:2345/` from any other device
on the same trusted network.

To update:

```bash
git pull --ff-only origin master
docker compose build --pull
docker compose up -d
```

Deploy from a terminal rather than a NAS management UI. Container managers
frequently ignore `docker-compose.override.yaml`, which silently drops your
volume paths and makes a healthy container look like it has lost your data.

### Managing the container

```bash
docker compose stop      # stop, keeping the container
docker compose start     # start it again without rebuilding
docker compose restart   # restart a running server
docker compose ps        # check it is up
docker compose logs --tail=100 marvel-lcg
```

`docker compose down` stops and removes the container and its network; the next
`up -d` recreates them, and your data is untouched because it lives in the bind
mounts rather than in the container. `down` is not needed for a normal update,
and `down -v` removes Docker-managed volumes — you almost never want it.

If a page still looks stale after an update, hard-refresh it (`Ctrl+F5`).

### Custom paths

`docker-compose.override.yaml` is gitignored and merges on top of the base
file, so machine-specific paths survive a `git pull`. Copy
`docker-compose.override.yaml.example` to start. Volumes are matched by their
container path, so an entry there **replaces** the base mount rather than adding
to it — check `docker compose config` after editing, and see
[Your data, and backing it up](#your-data-and-backing-it-up) for how to confirm
where things actually landed.

### Without Docker

Install Git, Python 3.10 or newer, and Node.js, then:

```bash
git clone https://github.com/nathancmaa/marvel-lcg.git
cd marvel-lcg
./run.sh
```

`run.sh` creates the virtual environment, installs dependencies, compiles the
frontend when it has changed, and starts the server. A systemd unit
(`marvel-lcg.service`) is included for running it as a service; see
[INSTALL-SERVER.md](INSTALL-SERVER.md).

## Your data, and backing it up

Everything the app remembers about you lives in a handful of places. Nothing
here is written anywhere else, and none of it leaves the machine.

### On the server

Paths are relative to the project directory, and all of them are configurable —
a Docker deployment maps them onto host folders through `volumes:` in
`docker-compose.yaml`, and an override file can point them somewhere else
entirely. If you are not certain where yours actually are, the running app says
so at startup:

```bash
docker logs <container> | grep -E "Game history ready|MarvelCDB decks"
```

and the definitive answer for a container is:

```bash
docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

| Path | What is in it | Worth backing up |
| --- | --- | --- |
| `runtime/statistics.sqlite3` | Game history, your product collection, matchup coverage, achievements, ratings and notes | **Yes — this is the one.** Everything else is replaceable |
| `deck/user-decks/` | Decks synced from MarvelCDB, each carrying its author's mulligan advice; plus `.marvelcdb-sync-state.json` | Yes, though a sync rebuilds it |
| `deck/campaign-decks/` | Decks frozen to in-progress campaigns | Yes, if a campaign is mid-run |
| `runtime/save_campaign_progress.json` | Campaign progress | Yes |
| `runtime/save_active_session.json` | The game you can resume from the start page | Only if one is in progress |
| `runtime/statistics.json` | Per-card statistics | Optional |
| `replays/` | Saved replays | Your call — they can be large |
| `assets/cache/` | Card images downloaded on demand | No. It rebuilds itself, and it is the largest folder here |

A backup is a file copy. Stop the app first if you can: `statistics.sqlite3` is
SQLite in WAL mode, and copying it while a game is being written can capture a
torn database.

```bash
docker compose down
tar czf marvel-backup-$(date +%F).tar.gz runtime deck/user-decks deck/campaign-decks
docker compose up -d
```

### In your browser

Some settings are held by the browser rather than the server, which means they
are per-device and are **not** in any server-side backup. They are also per
**origin**, not per machine: reaching the same container through a different
hostname — a Cloudflare tunnel beside a LAN address, say — is a different
browser as far as these are concerned, and each keeps its own copy.

The **MarvelCDB deck ID list is not one of these**, despite living in the
browser too. The server holds it in `deck/user-decks/.marvelcdb-sync-state.json`
and the settings page reads it back on load, so a new device or a new hostname
recovers the list rather than showing it empty.

Held only by the browser:

- BG Stats player name and location, animation speed, replay autosaving, and
  the deck and scenario filter preferences.
- **Card size.** Per-device on purpose: a laptop and an ultrawide want
  different answers, and one shared setting would mean changing it every time
  you moved between them.
- The keys chosen for OK, cancel, undo and the options on screen, and whether
  Quick Game is set up for two heroes.
- The Priority list of standing answers. This one is per game as well as per
  device: it is cleared when a new game starts, so there is nothing in it worth
  carrying anywhere.

Clearing site data for the app resets these and nothing else.

### Not data

The mulligan scoring weights are constants in
`game/render/mulligan_suggest.py` — source code that ships with the app, not
something the app accumulates. There is nothing there to back up, and a
reinstall gets the same values. What *is* yours is the per-deck advice written
by each deck's author, and that is stored with the deck in `deck/user-decks/`.

## Headless AI player

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

## Rules

This edition follows **Marvel Champions Rules Reference v1.8**. Card behaviour
is scripted per card rather than approximated, and solo timing — status cards,
damage, targeting, ability initiation — is the part most work goes into.

Release notes for every version are in [CHANGELOG.md](CHANGELOG.md).

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。
