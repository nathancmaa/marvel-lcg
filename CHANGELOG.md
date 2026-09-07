# Marvel Champions Digital: Ronin Edition Changelog

> Current release version: 0.7.4 — “Cerebro”

This document records the user-visible and development changes made in this
fork after it diverged from the original
[irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg) repository.

The comparison baseline is upstream commit
[`a77154a`](https://github.com/irefrixs/marvel-lcg/commit/a77154ab7e2f800a6ae82da6e67efd83dc3c8045)
(`master`, 2026-07-31). Version 0.6.0 is the first release carrying the
**Ronin Edition** name and the **Echo** codename.

Versions 0.7.2 and 0.7.3 were briefly published as 0.8.0 and 0.8.1 and were
renumbered onto the 0.7 line. Their tags and releases carry the new numbers
and point at the same commits; the commits that cut them still name the old
ones.

## Version 0.7.4 — “Cerebro” (2026-09-07)

Seeing what you have played, and moving games in and out of the app.

### Matchups

- A new tab in Collection & Statistics crosses every hero with every scenario,
  68 by 62, drawn from the catalogue rather than from the history: a grid of
  only what has been played cannot show what has not, which is the question a
  coverage table exists to answer.
- A square is light green where the matchup has been won, darker green where it
  has been won on expert, and red where it has been played without a win. An
  expert win sits on top of a standard one because it is the harder claim. Only
  decided games count; an abandoned game says nothing about how it went.
- Clicking a square opens Quick Game already set up — that hero selected, that
  scenario selected, the deck picker narrowed to that hero's own decks and the
  scenario box filter cleared so the tile is visible. The choice applies to that
  visit only and is not written back over what the picker usually opens on.
- The grid sizes its squares to the window, and this tab gives up the page's
  reading-width cap, which everything else keeps.
- Hero and villain names carry their box in a tooltip. A card panel was built
  for this and removed again: three attempts at making a floating panel dismiss
  reliably all failed, and it needs an approach that is not a hand-positioned
  element over a scrolling grid.

### Games in and out

- Every decided game on the Game History tab can be pushed to BG Stats. The play
  travels as one deep link with no account or key, and the app shows its own
  import dialog before saving. Two of the BG Stats fields fit this game exactly:
  a player's role is the hero, and the board is the scenario. Marvel Champions
  is win-or-loss, so the play carries no score.
- Marvel Champions Tracker exports can be read straight into game history, as
  physical plays by default or as digital. The .xlsx is parsed with the standard
  library, so the server gains an import screen without gaining a dependency.
- Plays are keyed on their own timestamp, hero and scenario, so re-importing the
  same export inserts nothing. A row whose hero or scenario cannot be matched is
  reported rather than stored under an approximation.

### Deck building

- Substitution suggestions are ranked on the traits a deck is actually built
  around rather than on any shared trait. A trait counts only where the deck
  both pays it off and can field it, weighted by how much of the deck is
  committed on both sides. 54 of a 96-deck collection have such a theme.
- Cards playable only by an identity carrying a named trait are excluded, the
  same way off-aspect cards already were. Sixty-eight player cards carry that
  clause and most heroes cannot play most of them.

### Fixes

- Side schemes overlapped the centre column on a 16:9 desktop and on a 4:3
  tablet. The stage now grows from the width the stylesheet asks for, which
  differs per layout, instead of assuming the base one.
- The right-hand button bar opens from an invisible strip against the screen
  edge rather than parking part of itself on screen.
- The start page reported 0.6.1 while running 0.7.3, and the test covering it
  asserted that same stale string, so it passed throughout. It now checks the
  version being built.
- z00lus is credited on the start page alongside Irefrixs.
- Frozen campaign decks had no mount of their own, so a rebuild took every
  in-progress campaign's deck with it.

## Version 0.7.3 — “Archive” (2026-09-06)

Building the deck you take in, and choosing how hard the game pushes back.

### Deck building

- Quick Game gained a third deck source beside My Decks and MarvelCDB deck:
  25 prebuilt aspect decks, each 30 aspect and basic cards with no hero cards
  at all, so any hero can carry one. A deck on MarvelCDB is always attached to
  a hero, which is why a good aspect list could not simply be lifted off one
  and handed to somebody else.
- Choosing that source reveals a hero dropdown beside the aspect deck
  dropdown, and puts the deck tiles away while it is in use. The tiles choose
  a deck, and an aspect deck replaces the deck, so they were asking a question
  whose answer was discarded. The hero keeps its identity, signature cards,
  obligation and nemesis set; only the player deck is replaced.
- The hero dropdown offers precons only, since a netdeck contributes nothing a
  precon does not here, and it opens on the precon for whoever was already
  selected rather than jumping to the top of the alphabet.
- Several of the lists are trait-locked — X-Men, Web-Warrior, Guardian,
  Avenger — and some name cards to swap out for a hero that does not fit. None
  of that is enforced: the deck's own notes say so, shown under the dropdowns,
  and the choice is the player's. The lists and notes come from a
  BoardGameGeek geeklist, credited and linked in the picker.

### Difficulty

- The Difficulty section can now be set to Standard I, II or III. Every game
  was previously dealt Standard I. The sets and their cards were already
  present and the engine already substituted difficulty sets by family; only
  the choice was missing.
- Standard II and III stand in for Standard I rather than stacking on it, and
  Expert still layers on top of whichever is chosen. The choice is remembered
  and always named in the section heading, as "Standard III" or
  "Expert · Standard III".
- Kingpin and The Wrecking Crew are dealt no Standard set at all. They disable
  the control and say why, rather than silently acquiring one.

### Deck titles

- The deck title in the Hero heading links to its page on MarvelCDB — for a
  synced deck picked off a tile as much as for one pasted in, and in aspect
  mode for the aspect deck. The link follows the endpoint the deck actually
  came from, so a deck pasted as a bare ID still resolves to the decklist it
  was fetched from rather than to a guess.
- Only decks this app fetched from MarvelCDB are linked. Precons carry a
  metadata url of their own — a Hall of Heroes article, and for one hero a
  bare image — and four of them point at marvelcdb.com without naming a deck
  page there.
- The "Precon" deck source is now called "My Decks", on both Quick Game and
  Campaign. It lists every synced deck alongside the starters and had been
  named after only half of what is in it.

### Fixes

- A reload left the deck source radio saying "Aspect deck" or "MarvelCDB deck"
  with its panel shut. The browser restores the checked radio; the picker
  assumed Precon regardless and now follows whichever radio came back.
- The Hero heading named whichever tile was selected even in aspect mode,
  where that tile's player deck is discarded — the one thing the summary could
  say that was not true.

## Version 0.7.2 — “Archive” (2026-09-06)

Finding what you want to play, and knowing what you own.

### Deck browsing

- The Quick Game scenario picker gained a controls bar to match the hero
  picker: filter to a single box, sort by new content, release order or name,
  and group by box. 62 scenarios in one flat list had become hard to search.
  Boxes are listed and grouped in the order they were released rather than
  alphabetically. All three settings are remembered.
- Heroes that share a name are told apart. Black Panther is both T'Challa and
  Shuri, and Spider-Man is both Peter Parker and Miles Morales; each pair
  collapsed into one entry in the hero filter and one heading when grouping.
  They are now keyed on the identity card and shown as, for example,
  "Black Panther (Shuri)". Both the picker and the Deck Viewer list 68 heroes
  where they listed 66.

### Collection

- The Deck Viewer compares a deck against the collection recorded in
  Collection & Stats, summarising how many cards come from products you have
  not marked as owned and naming those products, with an outline and a
  NOT OWNED badge on each such card. This is for moving between the digital
  and physical games; every card remains playable here regardless.
- Nothing is shown until a collection has been recorded. An empty collection
  means nobody has filled one in rather than that they own nothing.

## Version 0.7.1 — “Ronin” (2026-09-06)

Fixes for problems found while playing 0.7.0.

### Rules and cards

- **The Elephant's Trunk** can be used again. It reads "exhaust The
  Elephant's Trunk and up to 2 *other* Wakanda allies and/or supports", but
  it is itself a Wakanda support and was listed among its own optional
  targets — first, ahead of any real choice. Picking it exhausted the same
  card twice, which could not be paid, and the action failed outright. This
  is inherited from upstream and predates the fork.

### Decks

- A deck that names cards this installation does not implement is now
  reported when it syncs, in Settings and in the server log, instead of
  playing normally until the missing card comes up. The deck still syncs;
  it is playable up to that point.
- Asking for such a card no longer returns a server error. Listing an
  affected deck in the Deck Viewer put an assertion failure and a full
  traceback in the log for every missing card; the viewer already showed a
  placeholder, so only the noise and the failed request are gone.

## Version 0.7.0 — “Ronin” (2026-09-06)

First release of this fork, which continues from
[z00lus/marvel-lcg](https://github.com/z00lus/marvel-lcg) 0.6.1. It keeps that
edition's solo-first focus and adds two goals of its own: interface and
accessibility work, and getting finished games out to external trackers.

No rules or card behaviour changed in this release.

### Deck browsing

- The Quick Game hero picker gained a controls bar: filter to a single hero,
  sort by deck name, hero, aspect, or most recently updated, and toggles for
  grouping by hero and hiding precon decks. A synced collection reaches a few
  hundred decks, and one flat alphabetical list stopped being usable well
  before that. All four settings are remembered between sessions.
- Aspect is worked out from the cards a deck actually contains, since decks do
  not record it. Deadpool's own card class counts as an aspect for this
  purpose, so his decks are grouped as themselves instead of appearing to have
  none. The card database this needs is only fetched the first time aspect
  sorting is used.
- The Deck Viewer gained matching toggles: grouping replaces the My decks /
  Starter decks split with one group per hero, and precons can be hidden.
- The Deck Viewer now links a deck back to its MarvelCDB page, next to Share
  Deck. Starter and hand-built decks have no source to link to and show
  nothing.

### MarvelCDB syncing

- A bare deck number now resolves to a **published decklist** first rather than
  a personally shared deck. The two are separate MarvelCDB records that share
  their numbering, so a number copied while browsing the site — which is
  almost always a decklist — could quietly sync an unrelated deck instead.
- Synced decks are named after the endpoint they actually came from, so a
  `deck` and a `decklist` sharing a number can coexist. An older bare-numbered
  file for the same deck is removed once its replacement is safely written, and
  only when it is recognisably a synced file, so a hand-built deck that happens
  to share the name is left alone.

### Interface

- The board now widens to fill displays wider than 16:9 instead of being
  letterboxed with the extra width unused. On a 3440x1440 screen that is about
  five more card widths of room in each row.
- Rows no longer compress far enough to slide underneath the deck and discard
  columns, which a hero carrying enough upgrades could previously do.
- The prompt asking you to choose a target no longer covers the cards it is
  asking about. It moves the shortest distance that clears every highlighted
  card, stays put when there is no conflict, and is left alone entirely if you
  have dragged it somewhere yourself.
- The right-hand button bar keeps a usable strip on screen instead of a few
  pixels, so Log, Undo, Redo and QSave can be reached without hunting for the
  edge of the screen. Swiping left to open it on a touch screen now works; the
  gesture had been wired up but never moved anything.

### Server and deployment

- User decks are stored outside the container, so decks synced from MarvelCDB
  survive `docker compose up --build`. They previously lived in the image and
  were lost on every rebuild.
- Compose files use the `.yaml` extension, and a `docker-compose.override.yaml`
  is read for host-specific paths and settings while staying out of version
  control. Several installations can run on one host by setting a project name
  and container name; examples for both are included.
- JSON endpoints are cached for an hour rather than a year, so updated card
  data is picked up without clearing browser storage. Versioned assets are
  unaffected and keep their long-lived cache.

## Version 0.6.1 — “Echo” (2026-08-28)

### Rules and cards

- Added **Stop the Presses!** in Standard and Expert modes, including seeded
  Daily Bugle Persona setup, stamina management, all four Persona abilities,
  and the required Tombstone and Tracksuit Mafia modular sets.
- Added **Protection Racket** in Standard and Expert modes with all five main
  scheme variants, deterministic solo setup, and the **Disasters** and
  **Tracksuit Mafia** modular sets.
- Added **Electro** as a selectable Fear No Evil underling for The Getaway,
  including all three villain stages, Electric Charge, and his complete
  encounter set in Standard and Expert games.
- Added **Purple Man** as a selectable Fear No Evil underling across all
  implemented mix-and-match scenarios, including INFLUENCED minions,
  command obligations, Converted allies, and his complete encounter set.
- Added **Hammerhead** as a selectable underling with all three villain
  stages, status-driven Headbutt behavior, Chameleon, and the full Maggia
  encounter set.
- Added **Typhoid Mary** as a selectable underling with her two-sided villain
  stages, Disturbed Psyche victory track, Mary Walker/Establish Trust cycle,
  and complete encounter set.
- Added the fixed **Kingpin** finale in Standard and Expert modes, including
  nemesis/UNDERLING setup, the two-stage main scheme, Public Support, and the
  complete Kingpin encounter set.
- Extended all five mix-and-match scenarios to offer every Fear No Evil
  underling, with the new choices and Kingpin marked clearly in Quick Game.
- Added **Art Museum Heist** in Standard and Expert modes, with deterministic
  ART attachment setup, all five underling choices, and
  the complete **The Owl** encounter set.
- Added **The Raft Breakout** in Standard and Expert modes, including Master
  Key setup, PRISONER minions, Imprisoned, all five underling choices, and the
  complete **Tombstone** encounter set.
- Added an explicit pre-attachment timing message for facedown boost cards so
  effects such as Public Support can replace the boost without consuming or
  misplacing the top encounter card.
- Corrected player-side-scheme rewards so cards such as Sidearm enter the
  proper player area instead of remaining detached on the table.
- Corrected Photographic Reflexes resolution and exclusive thwart-target
  restrictions such as Hope Summers being limited to Stryfe's Grasp.
- Added **Jessica Jones** with her identity cards, obligation, nemesis set,
  starter deck, and the additional cards required by her integration.
- Added readable text-only card images for implemented cards whose published
  artwork is unavailable, including title, type, cost, resources, traits,
  statistics, and rules text.
- Refreshed the availability of events tucked beneath Echo after the game
  state changes, so cards such as Army of One can be played at the correct
  time through Photographic Reflexes.
- Corrected reported Fear No Evil interactions: Contingency Planning now
  recognises printed attachment targets, Daredevil has his printed THW 2,
  Superior Taste follows the Rules Reference definition of “you”, and Raised
  by the Kingpin tracks the player who received the obligation.

### Interface

- Distinguished Retaliate damage from ordinary card activation in the game
  log.
- Removed the duplicate `was defeated` log entry emitted for defeated schemes.
- Added a prominent reminder that Ronin Edition is a testing and learning
  platform and is not a replacement for supporting the physical card game.
- Replaced the standalone Statistics page with a combined **Collection &
  Statistics** screen for tracking owned physical products, browsing game
  history, and reviewing achievements.
- Added a **Proxy** screen that produces print-ready A4 PDFs with cut lines for
  hero decks and scenarios belonging to catalogued out-of-print products.
  Eligibility is enforced on both the browser and server sides.
- Added a **Deck Viewer** for inspecting local and synced decks, showing each
  card's source product, and exporting a compact shareable PNG deck grid.
- Organised Quick Game heroes alphabetically within custom-deck and preconstructed
  groups, and grouped scenarios visually by expansion or scenario pack.
- Restyled the main menu and in-game controls, added a return-to-menu action to
  the game-over screen, and compacted the desktop table for clearer recording
  and play.
- Corrected fallback image caching so newly available card art can replace a
  previously generated placeholder after restart.

### Game history and achievements

- Added manual logging, editing, and deletion of physical solo games.
- Unified digital games, replay imports, and tabletop results in the same
  SQLite history, with source filters and shared hero, villain, and matchup
  win rates.
- Recalculate achievement progress after a physical result is corrected or
  removed, and order streak achievements by the actual played date.
- Added optional independent 1–5 star ratings for the hero and scenario after
  a completed game, with ratings stored alongside the game-history record.

### Automation and regression coverage

- Added an authenticated headless solo-play API, a local MCP bridge, and a
  repository-scoped Codex skill for running complete games without the browser
  UI. Agent-run games retain replays but are excluded from personal history,
  statistics, ratings, and achievements.
- Added a real-engine puzzle regression suite covering 20 compact rules and
  card-interaction cases, with isolated server lifecycle and cleanup.

## Version 0.6.0 — “Echo” (2026-08-11)

This is the first Ronin Edition release. The Rules Reference 1.8 work and the
fork changes described below are included in the `master` branch.

### Rules engine

- Made Rules Reference 1.8 the single runtime rules model and removed the old
  v1.6/v1.7/v1.8 behavior switches from game execution.
- Added explicit timing and priority handling for interrupts, responses,
  forced abilities, constant abilities, status cards, and simultaneous
  effects.
- Reworked ability initiation so legality, targets, costs, payment, and effect
  resolution occur in the required order and failed initiations cleanly roll
  back temporary state.
- Added deterministic surge queuing and corrected reveal, boost, quickstrike,
  overkill, indirect damage, and calculated-damage processing.
- Corrected referential targeting, target validation, card swaps, card
  ownership/control, uniqueness, permanent cards, restricted cards, counters,
  modifiers, and card-state transitions.
- Implemented cumulative rules needed from Rules Reference 1.7, including
  `otherwise`, `for each`, player choices, actions and activations, setup,
  attacks, villain-stage transitions, and the definition of “you”.
- Consolidated keyword and status handling into the normal event/message
  pipeline instead of retaining legacy ad-hoc execution paths.

### Cards and data

- Updated affected card scripts and metadata to follow the 1.8 timing,
  targeting, initiation, cost, status, and errata rules.
- Added focused corrections for cards from Black Panther, Core/Ultron,
  Falcon, Galaxy's Most Wanted, Iceman, Magneto, Ms. Marvel, and Psylocke.
- Regenerated the card database checksum after metadata corrections.

### Saves, replays, and UI

- New games always record the `v18_all` rules marker.
- Saves and replays created under older rules models are intentionally
  incompatible and now fail early with a clear compatibility error.
- Removed legacy rules toggles from new-game payloads and browser state.
- Updated setup and replay pages for the single-version rules model.

### Tests and documentation

- Added focused unit coverage for timing priority, defined terms, ability
  initiation, surge, reveal lifecycle, damage, overkill, targeting, swaps,
  setup, UI payloads, replay compatibility, card errata, and miscellaneous 1.8
  rules.
- Added cumulative 1.7 coverage for choices, ownership/control, referential
  abilities, uniqueness, actions/costs, counters/modifiers, attacks, villain
  transitions, setup, and “you”.
- Added a small self-contained v1.8 replay fixture so replay loading can be
  tested without the external upstream replay corpus.
- Added [`docs/rules_v18_compliance.md`](docs/rules_v18_compliance.md), updated
  the engine architecture and card scripting guides, and documented the
  v1.8-only policy in the repository guidance.
- Documented the use of a local, Git-ignored Rules Reference 1.8 copy under
  `rules/` for future rules audits and card validation.

## Fork changes since upstream

### Solo-first game setup

- Added a streamlined **Quick Game** screen focused on one hero versus one
  scenario.
- Added direct selection of prepared starter decks from `deck/starter/`, so a
  player does not need to upload a deck file before every game.
- Remembered the last selected hero and scenario in browser `localStorage` and
  restored them after a reload.
- Disabled **Play** until both required selections are valid and added a
  loading state to prevent accidental double game creation.
- Kept the advanced setup screen available while making the simplified solo
  flow the default path for a new game.
- Standardized the new and advanced setup additions on English UI text.

### Campaigns

- Added a separate solo-oriented **Campaign** screen for starting a campaign
  or continuing a saved one.
- Made the current campaign scenario automatic while retaining simple starter
  deck selection and **Play / Continue Campaign** actions.
- Added campaign selection, stable campaign identifiers, saved campaign state,
  card previews, and improved MarvelCDB campaign deck imports.
- Added or completed campaigns for:
  - Mutant Genesis;
  - NeXt Evolution;
  - Age of Apocalypse;
  - Agents of S.H.I.E.L.D.;
  - Galaxy's Most Wanted;
  - The Mad Titan's Shadow.
- Audited campaign transitions and campaign card scripts, corrected Magneto's
  campaign power attachment, and applied remaining hero health correctly in
  standard campaign mode.
- The initial campaign implementation was integrated from
  [sdolle1775/marvel-lcg](https://github.com/sdolle1775/marvel-lcg) and then
  adapted, audited, and fixed for this fork.

### Heroes and player cards

- Added original integrations for **Echo**, **Wonder Man**, and **Daredevil**,
  including identities, hero cards, obligations, nemesis sets, metadata, and
  starter decks.
- Added Daredevil's separate Sense deck and exposed it as a labeled auxiliary
  player deck on the table.
- Completed Wonder Man's unfinished integration and corrected, among other
  behavior:
  - Mr. Hollywood resource generation and overpayment;
  - Ionic Psychology's contribution to hero attack;
  - Stronger Together defense and interruption flow;
  - Pacifism removal choices and readable obligation prompts;
  - ally, resource, discard, damage, and edge-case interactions.
- Added targeted Wonder Man card tests, system tests for indirect damage, and
  replay-oriented coverage for the new hero mechanics.
- Integrated the initial **Hercules** implementation from
  [sdolle1775/marvel-lcg](https://github.com/sdolle1775/marvel-lcg), then fixed
  its card scripts and setup behavior locally.
- Added and labeled Hercules' Labor and Gifts auxiliary decks, positioned them
  near the player area, and corrected the Protect Humanity initiator crash and
  other hero-specific timing/targeting issues.

### Replays and post-game flow

- Fixed **Save Replay** so completed games are persisted by the server instead
  of only reporting success in the browser.
- Added replay discovery, loading, downloading, and playback from the browser.
- Added an in-game replay control bar with first/previous/play-pause/next/last
  controls, a position counter, and a seek slider.
- Made replay playback open on the first recorded state and remain paused until
  the player starts it.
- Positioned the controls as a bottom-right overlay so they do not resize the
  table or cover the player's hand.
- Preserved deterministic step-forward, step-backward, seek, and restart
  behavior through the existing replay reconstruction model.
- Added a post-game **Try Again** action that starts the same setup with a new
  random seed.
- Excluded personal replay files and game notes from version control.

### Browser UI and controls

- Added an animation-speed slider to the advanced settings screen.
- Added readable descriptions beside advanced rule options.
- Fixed character encoding for the added settings text.
- Corrected keyboard shortcuts so they use the same guarded actions as pointer
  controls and respect disabled or paused states.
- Improved auxiliary deck rendering and labels for player-owned special decks.
- Made missing static resources such as `mask.svg` return a normal HTTP 404
  instead of crashing the file request handler with an assertion.
- Added clearer end-game statistics and replay actions without disturbing the
  game-table layout.

### Linux server and lifecycle

- Added `run.sh` as the preferred Linux launcher. It creates the virtual
  environment, installs requirements when needed, compiles stale TypeScript,
  checks port `2345`, and launches the server.
- Added missing runtime dependencies such as NumPy to the installation path.
- Added LAN-oriented binding so the Linux server can run on a small host while
  play happens in a browser on another device.
- Added [`marvel-lcg.service`](marvel-lcg.service) for a dedicated
  `marvel-lcg` system user and `/opt/marvel-lcg` working directory.
- Added [`INSTALL-SERVER.md`](INSTALL-SERVER.md) with installation, user,
  virtualenv, systemd, logging, and update instructions.
- Improved startup failure handling when the configured port is already in use
  and prevented crash saving from assuming a game object exists before engine
  initialization completes.
- Improved aiohttp shutdown and client-disconnect handling to reduce pending
  task and cleanup errors.

### Project documentation and maintenance

- Added [`AGENTS.md`](AGENTS.md) with architecture, validation, card scripting,
  frontend, replay, asset, and deployment guidance for coding agents.
- Added [`FORK-GOALS.md`](FORK-GOALS.md) to state the fork's concise priorities:
  simple solo play, a simplified UI, and reliable Linux hosting.
- Expanded the README progress section and added a current UI screenshot.
- Added the README progress image and documented which work originated in the
  community fork versus which hero integrations were developed locally.
- Updated ignore rules for downloaded assets, generated frontend files,
  runtime saves/replays/statistics/crashes, private notes, and local task files.

## Commit inventory

This is the complete committed history between the upstream baseline and the
current fork `master`, in ancestry order. The Rules Reference 1.8 work above is
committed separately on `feature/rules-v18` and therefore does not appear in
this `master` inventory.

- 2026-08-04 [`9a3fc26`] Add Linux server setup and UI improvements
- 2026-08-04 [`3a2c3b8`] Fix game hotkey handling
- 2026-08-04 [`4a2313f`] Add repository guidance for coding agents
- 2026-08-04 [`d5dac18`] Add streamlined solo game setup
- 2026-08-04 [`2900d19`] Add reliable replay saving and playback controls
- 2026-08-04 [`865ce56`] Add Echo hero pack integration
- 2026-08-05 [`7af3e5f`] Add Wonder Man hero pack integration
- 2026-08-05 [`fb5cbea`] Fix Wonder Man gameplay issues
- 2026-08-05 [`4702730`] Fix Wonder Man resource and attack handling
- 2026-08-05 [`d97935a`] Add Wonder Man card and replay tests
- 2026-08-05 [`99dc350`] Use English for game setup UI
- 2026-08-02 [`5f35b65`] Improve campaign card previews
- 2026-08-02 [`eb8d10c`] Implement Mutant Genesis campaign setup
- 2026-08-02 [`c01d20e`] Add campaign selector and identifiers
- 2026-08-02 [`30a9b07`] Implement NeXt Evolution campaign
- 2026-08-02 [`e9ce484`] Implement Age of Apocalypse campaign
- 2026-08-03 [`ed1bc29`] Implement Agents of SHIELD campaign
- 2026-08-03 [`c12c672`] Implement Galaxy's Most Wanted campaign
- 2026-08-03 [`d72195c`] Implement Mad Titan's Shadow campaign
- 2026-08-04 [`deaae23`] Fix Magneto campaign power attachment
- 2026-08-04 [`8b80803`] Audit campaign card transitions
- 2026-08-04 [`c3b00fb`] Audit all campaign card scripts
- 2026-08-05 [`1c515ca`] Apply campaign remaining health in standard mode
- 2026-08-05 [`2d8a204`] Improve MarvelCDB campaign deck imports
- 2026-08-05 [`239b727`] Integrate Hercules hero pack
- 2026-08-05 [`6e82ac5`] Add solo campaign flow and harden Hercules cards
- 2026-08-06 [`d58ca0a`] Add Daredevil hero integration
- 2026-08-06 [`3f5c403`] Document fork progress

## Compatibility and scope

- The supported target is solo play with one hero and a browser connected to a
  Linux-hosted server. Multiplayer and PvP expansion are not fork priorities.
- On the Rules Reference 1.8 development line, old saves and replays are not
  supported; only newly recorded `v18_all` data is accepted.
- Downloaded card art, local cache files, personal decks, saves, replays, and
  notes are intentionally not distributed by this repository.
- Generated JavaScript is not committed; TypeScript sources must be compiled
  during local setup or deployment.
