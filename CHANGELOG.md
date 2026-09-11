# Marvel Champions Digital: Cerebro Changelog

> Current release version: 0.7.11

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

## Version 0.7.11.1 (2026-09-11)

The stand-in card art stops needing a person, and starts replacing itself.

- **Nothing to run.** 0.7.11 shipped the Jessica Jones and Luke Cage art as a
  script to be run by hand against each installation. It is gone. The mapping
  it carried is `data/card_images.json`, and the image cache reads it as what
  it always was — a source, tried after every server in `launch.json` and only
  when none of them has the card. The pictures arrive the first time a card is
  looked at, the same way every other pack's do.
- **And it can improve now.** The script wrote into `assets/pics/`, which is
  the folder for art you supply yourself and therefore beats everything, for
  good. Fan sites publish scans of a new pack months before Cerebro and
  MarvelCDB do, so that was the wrong shelf: those files would still have been
  the ones on screen a year after the official ones appeared. They go to the
  ordinary download cache instead, and each is noted in a small index beside
  it.
- **The sync thread does the asking.** It is the one thing here that already
  wakes on a timer, so it offers every card in that index back to the image
  servers — once on the way in, and after each deck sync. The first server
  that answers replaces the file and forgets the entry, so the index empties
  itself as the official art catches up and a table that is fully covered does
  no work at all. A server refusing a card it has not published yet is the
  expected answer and is logged as one; seventy-odd cards refusing twice a day
  is not a log worth keeping.
- If you ran the old script against a deployment, the files it left in
  `assets/pics/` will still win. Deleting the `61` and `62` images from that
  folder hands the job back to the cache.

## Version 0.7.11 (2026-09-11)

Three products that had been out for a while and were not here.

- **Jessica Jones is finished.** The pack's hero half has been playable since
  0.7.9; its other half — Captain Marvel, Spider-Woman, Squirrel Girl,
  Grapnel Launcher, Entrapment, Shakedown, Echo as an ally, the three Innate
  upgrades — was not here at all, so any netdeck reaching for them found them
  missing, which in true solo announces itself in the middle of a turn. All
  twenty are in. Three of them are reprints and point at the printing that
  already carries the rules rather than repeating it. **Run Them to Ground**
  needed the engine to learn to skip a villain phase, which nothing had asked
  for before: a skipped phase still opens and closes, and what it loses is its
  contents, so end-of-phase cleanups do not go missing with it. Also fixed:
  the Luke Cage ally's printed wild icon was written "W", which is not a
  resource code — the parser counts r, b, y and g and ignores the rest — so
  the card had been showing no icon at all since the pack landed.
- **Luke Cage.** Thirty-eight cards, the pack's own published Leadership deck
  as his starter, and Cottonmouth's Serpent Society as his nemesis set. The
  whole pack is built on tough status cards, and the engine already knew how
  to hold more than one of them. What it did not have was **unpreventable
  damage** — Luke Cage's own forced response and Internal Injury both print
  the word, and without it Metal Bracer, in the same deck, would have shrugged
  off the damage that is meant to be the price of his skin.
- **Synthezoid Smackdown**, played the way this app already plays Civil War's
  four leaders: you fight She-Hulk or Vision, their main scheme is the one
  threatening you, and the other team is simply not on the table. Two
  scenarios with expert variants, eight modular sets, both leaders' own sets.
  The pack is written for two teams playing against each other and that half
  is not here — the eight cards belonging to the leader's own player say "your
  leader" or "the enemy leader's main scheme", and a hero has neither, so they
  are left out rather than shipped inert.
- **Card art for the two hero packs** comes from Hall of Heroes, which is the
  only place publishing scans of them; Cerebro and MarvelCDB have nothing in
  the 61xxx and 62xxx ranges yet. The mapping ships as a script,
  `tools/fetch_pack_images.py`, and the images themselves do not: this
  installation has always fetched card art rather than carried it. Run it once
  against a deployment and the pictures stay put. Three cards have no scan
  anywhere and fall back to a readable text face. Synthezoid needs none of
  this — Cerebro carries the whole 57xxx range.
- **A deck name gets the room it always had.** The heading beside the hero
  grid puts the step number on the left and the selected deck on the right and
  never claimed the space between them, so a deck called "Nein Freund" was cut
  to "Nei..." with a thousand pixels of nothing beside it. A name longer than
  the whole row still ends in an ellipsis, which is what that was for.

## Version 0.7.10 (2026-09-11)

The rules to hand, the cards at your own size, and a deck that says what is
wrong with it.

- **A quick reference for the keywords and the icons.** **Reference** in the
  options panel opens the 26 keywords and 13 icons the game puts on the
  board -- Guard, Peril, Steady, Uses, the acceleration and hazard marks -- in
  the official reference's own wording rather than a paraphrase, because a
  rules reference that is nearly right is worse than none. Each icon row draws
  the app's own mark, so you are looking at the same thing that is on the
  card. Type in the filter to cut the list down; the X closes it. Opening it
  closes the options panel behind it.
- **The cards can be made smaller.** A slider in Settings, and a second one in
  the right-hand pane so it can be moved mid-game, takes every card from full
  size down to half in steps of five percent. It is a per-device setting and
  stays in the browser: an ultrawide and a laptop want different answers, and
  a size chosen on one should not follow you to the other. A card's contents
  scale with its frame -- text, stat lines, icons -- which they did not at
  first, and a shrunken scheme spilling its text past its own edge is what
  said so.
- **A deck says what is wrong with it, and still plays.** The deck viewer now
  reads a deck against the rules and prints what it finds: under forty cards
  counting signature cards, more copies of a card than it allows, cards from
  more than one aspect, cards gated on an identity trait this hero does not
  have, and cards this installation has not implemented. None of it refuses
  anything. This is a solo table, the rules are yours to bend, and a netdeck
  built around a card that is not here may be worth trying anyway -- what
  costs a game is finding out mid-turn.
- **Stacking, rebuilt around what a card can do.** The stack a character's
  passive upgrades collapse into is now one stack rather than one per card,
  sits in front of the character rather than behind whatever happened to be
  exhausted, and does not take cards in and out as the board changes. What
  stays out of it is the important part: a card you might spend for its
  resources is a card you need to reach, and the index the first attempt
  trusted reports four such cards where the printed text says fifty-nine. The
  rule now reads the Resource line off the card itself. Encounter cards never
  collapse.
- **An option key answers the question.** The home-row keys that pick from a
  prompt -- Attack, Thwart, Change Form -- now confirm the choice as well as
  make it, so the common answer is one key rather than a key and then z. A
  choice that still needs a target picked stops and lets you pick it. There is
  also a second confirm button directly beneath the options, for the prompts
  that open far enough from the bar to make the trip worth saving.
- **One hero or two, where the choosing happens.** The two-handed setting is a
  1P/2P switch at the top of the Settings pane instead of a checkbox in a
  list. Quick Game rolls for the standard, expert, or heroic set from a die
  beside the dropdown. In two-handed play the other player's hand collapses
  out of the way from the left pane, and a matchup's details name both decks
  rather than one.
- **The end-of-game card statistics are one row per card.** Three copies of
  Energy were three rows saying a third of the story each; they are now one
  row, totalled, saying how many of that card the deck held.
- **The matchup grid is grouped by product.** Heroes run in their box's order
  under a label on its side down the left edge, villains under a bracket
  across the top, and both labels disappear when the grid is re-sorted by
  completion, where they would be lying about the order. The column headers
  stagger so the box name is still readable once the page has scrolled.
- **Smaller things.** The log menu is now **Options** and closes from an X on
  its own pane rather than from inside the log window. The deck sync says so
  in the log when it declines to prune a file, instead of declining in
  silence. The README no longer claims a new device loses the list of decks
  you have imported -- that list is on the server and comes back on its own.

## Version 0.7.9 (2026-09-10)

Answering the same question for the tenth time, without answering it again.

- **Standing answers, and the Priority list.** A card with an optional
  Response or Interrupt now carries a tick. Tick it and the game stops asking
  about it: when that window comes round, the card answers for itself. The new
  **Priority** panel, on the right-hand bar beside Log and Deck, is the list of
  everything you have ticked, in the order it fires. That order is the point of
  the panel -- when a defeated side scheme offers Mission Leader and Graymalkin
  in the same breath, the game resolves the higher one and the next ask brings
  the other. Move a card up or down with the arrows, drop it off the list to be
  asked again, and hover a name to see the card. The list belongs to the game on
  the table and is cleared when a new one starts: a standing answer is a
  decision about this deck against this villain, not a setting.
- **It answers questions, and nothing else.** A tick is not permission to act
  for you. It applies only in a Response or Interrupt window -- never to a
  character's actions or basic powers, so a ticked ally does not attack the
  moment you click her -- and never to a forced trigger, which resolves itself
  and was never a question. Nothing is ever declined on your behalf: an
  unticked card asks every single time, so a card you forgot was in play is a
  prompt rather than a silent miss. And the tick only appears where it means
  something: on a mid-game board, eight cards of twenty-three rather than all
  of them.
- **One switch instead of two.** "Auto Activate" and "Show Auto Activate
  Checkbox" were one feature split in half, and the half that put the tick on
  the cards was off by default -- which left the other half with nothing marked
  and no way to mark it. They are now a single **Auto Answer** in the log menu:
  off means no ticks and no answers. A ticked card also stopped wearing a
  warning colour; it takes the Priority panel's own accent, so the mark on the
  board and the row in the panel read as the same thing.
- **A key for undo, and a key for every option.** Undo was ctrl+z and nothing
  else, the only common answer still needing both hands; it now takes a bare
  key too, defaulting to **c**, beside the z and x that already answer OK and
  cancel. When the game offers a choice -- Attack, Thwart, Change Form -- the
  **home row takes them**, left to right, with each key drawn on its own
  button. All of these are remappable in Settings, and a key you choose now
  beats whatever the table did with it by default, rather than winning or
  losing by accident of ordering. Clashes are explained rather than refused.
- **Passive upgrades stack.** A hero or ally that has collected five upgrades
  was taking five card widths of a row that has to hold everything else too,
  and most of those upgrades are a stat line you read once and never touch.
  Those now stack behind each other with an edge showing -- still hoverable, so
  a sliver is a full preview -- and **Stack Passives** in the log menu turns it
  off for a row you want to read whole. Only upgrades with nothing to click:
  one that carries an Action, Response or Interrupt stays where you can reach
  it. An ally's three stat upgrades go from 508 pixels of row to 300.
- **A row that overflows stays readable.** The squeeze applied to a crowded row
  was the same for every gap regardless of how wide it started, so a long
  enough row closed its narrowest gaps and then pushed cards past each other
  into the wrong order. Every gap now holds open by an edge.

## Version 0.7.8 (2026-09-09)

Two heroes at once, a deck for every hero, and the statistics behind both.

- **Two-handed solo.** One person playing two heroes from one screen, off by
  default and turned on in Settings. Quick Game's hero section then grows P1
  and P2 tabs and nothing else changes: the grid is still one selection at a
  time, and the tabs say who that selection is for. Each tab keeps its hero
  and the deck chosen for them, so a netdeck picked for P1 is still theirs
  after a visit to P2. The game itself is the hot seat the engine has had
  since irefrixs's first commit -- the replay viewer was already using it, and
  this fork had only stopped offering a way in.
- **A win counts for every hero who was there.** Game history records who
  played a game as well as how it went, so a two-handed win lights both
  heroes' squares on the coverage grid while remaining one game, one win, one
  entry in the recent list. Every game already recorded keeps the seat it
  always implicitly had. The limit is four, which is the game's own rather
  than this app's.
- **The universal decks.** One prebuilt deck per hero, from the geeklist the
  aspect decks came from, as a fourth deck source on Quick Game. There is
  nothing to choose in it: the deck belongs to the hero, so picking the hero
  picks the deck. 54 of the 69 are here; the rest name cards this
  installation does not implement, and a deck that would fail when a card is
  drawn is not shipped. Built by a script from the list's own sheet, so it can
  be rebuilt when a pack lands rather than trusted.
- **Favourite decks are shared between devices.** They were in the browser,
  which meant a deck starred on the laptop was not starred on the phone
  against the same container. They now live beside the collection, which has
  always worked that way.
- **Quick Game reads better.** Villains are listed in their box's order rather
  than alphabetically -- the Core Set opens with Rhino, not Klaw. A villain
  tile's mark says whether the hero you have chosen has beaten them, not
  whether anybody has. Arriving from a coverage square opens on that square's
  box instead of all sixty-two. "Favorites only" and "Hide precons" survive a
  refresh, which neither did.
- **The coverage grid remembers its controls**, so sorting by completion is a
  choice made once. "Played only" now hides unplayed heroes and keeps every
  villain: an unplayed villain is the square worth looking at.
- **The fork has its own icon**, and the game log has stopped naming its own
  internals -- "Cable's deck was shuffled with Cable's discard pile" rather
  than "PlayerDeck<40>", and "1 first player token" rather than a quoted
  variable.
- **Game history stopped leaking database connections.** Every operation
  opened one and never closed it, for as long as the container was up. This
  was also what made eighteen tests fail on Windows and nowhere else, which is
  why it went unread for months.

## Version 0.7.7 (2026-09-08)

Five additions to the pickers and the deck viewer, and one fix to the game
log.

- **Decks can be starred, and either picker narrowed to your favourites.** A
  star sits on every Quick Game tile and beside the deck viewer's dropdown,
  and "Favorites only" works the way "Hide precons" already does. One list
  rather than two: a hero starred while choosing a game is starred while
  browsing decks, and the viewer marks them with a star in its dropdown, since
  a native list cannot carry a control on each line.
- **The deck viewer says how the games went** -- win-loss and a percentage for
  the deck, and for the hero behind it, or 0-0 for a deck that has never been
  to the table. Decks are grouped by the name the game recorded, so two decks
  sharing a name share a record: the name is all a finished game keeps of
  which deck was played, and a wrong split would be worse than a merge.
- **Villain tiles say which scenarios have been beaten, and at what.** A mark
  along the bottom of the tile in the colour the coverage grid uses for the
  same thing, taking the hardest clear by any hero -- exactly what that grid's
  own column headers answer. The ladder is now read from one place by both
  pages rather than written down twice.
- **The villain picker steps through the boxes.** Working through them in
  order is a real way to play this game, and doing it from the dropdown meant
  opening it and finding the next line every time. The control only appears
  while a box is selected: with every box showing there is no sequence to be
  at a point in.
- **Settings lists the decks being kept in step with MarvelCDB** -- deck,
  hero, the ID linked to the page it came from, and whether it synced, failed,
  or names cards this installation cannot play. The rows come from the
  configured IDs rather than the last success, so a deck that failed still has
  a row saying so. It scrolls in a panel of its own, because a row per deck is
  as long as your collection.
- **Internal names no longer appear in the game log.** It read "Cable's
  PlayerDeck<40> was shuffled with Cable's DiscardPile<0>" and "placed 1
  'first_player_token' token": decks were being formatted with the debug
  representation, and token names are identifiers that were quoted in as they
  stand. Both now read as English. The debug form is kept where debugging
  looks for it.

## Version 0.7.6.1 (2026-09-07)

Two bugs found in play, both older than this fork, and four things that make
the coverage grid and Quick Game easier to use.

- **A solo Kang game no longer crashes when an aspect is defeated.** Kang
  gathers the players out of the defeated aspect's game area into the first
  one, which in a solo game is frequently the area the player is already
  standing in -- and moving a player into their own area walked every card they
  own into an assertion that a card is not already where it is being put.
  Upstream: game_area.py and every Kang card have only ever been touched by
  irefrixs.
- **Teleport Drop is playable again** when a Bamf is attached to an enemy.
  Availability is decided before the target is chosen, and the discard cost was
  reading the target list while it was still empty -- so it reported a cost it
  could not pay and the card sat dead in hand. A z00lus regression from moving
  the cost from payment time to validation time; the test that shipped with it
  hands the cost an effect that already has its targets, so it passed
  throughout.
- **The coverage grid sorts**, by box, name, or how far through each hero you
  are, with that percentage beside each hero's name. Headers also carry a thin
  stripe in the colour of the hardest difficulty beaten along that row or
  column.
- **Clicking a coverage square plays your deck**, not the precon. The grid is
  built from starter decks so a square only has a precon id to send; it now
  locates the hero and hands over to one of your own decks for them.
- **Quick Game says what is about to start** -- hero, the deck actually going to
  the table, villain and difficulty, beside the Play button. The three choices
  live in three sections up the page, and after a browser back or a refresh
  they are restored rather than chosen, which is when it is worth checking.
- **The bug report window is gone.** Its Upload button answered "Upload is
  disable in Open Source version" and did nothing; it was the closed-source
  product's telemetry path, still promising to collect your operating system
  and browser. Share replay went the same way -- it called the same dead
  upload. Save replay is a different path and still works. The error dialog and
  its traceback stay: that text is how a crash gets read.

## Version 0.7.6 (2026-09-07)

The fork has one name now. It is **Marvel Champions Digital: Cerebro**, and
releases carry a number rather than a codename of their own. Echo, Ronin,
Archive and Cerebro named four versions between them and then stopped earning
their keep: a codename dates a build without saying anything about it, and a
release nobody can refer to by number is harder to talk about, not easier.
Cerebro is the name that stayed. Earlier entries below keep the names they
shipped under.

- Renamed throughout: the product name, every page title, the archive
  eyebrows, the credits page, the theme stylesheet, the docs and the MCP
  tooling. `RELEASE_CODENAME` is gone from build.py, so a release is a number.
- Three things deliberately still say ronin, each with a reason written beside
  it: the card-image cache revision and its client-side twin, where the value
  is part of every cached filename and changing it would throw the whole image
  cache away; and a browser flag recording that a one-off settings migration
  has already run, which renaming would run again.
- The hand-written `?ronin-session=1` on the Quick Game and Campaign links is
  gone, along with the matching busters on scripts and stylesheets. Nothing
  ever read the query parameter, pages are served `no-cache`, and every css and
  js reference is rewritten to a content-hashed `/v/<token>/` URL at serve
  time -- so they busted nothing and only went stale. The favicon's buster is
  kept and renamed, because that one is still doing the job: the rewriter
  versions css and js, not icons.

Also in this release:

- **Heroic, end to end.** It was always in the engine and only reachable from
  Advanced Setup; Quick Game now offers it, and games record the level they
  were played at. Each square on the coverage grid shows the hardest
  difficulty that pairing has been beaten at -- Standard, Expert, then Heroic
  by level in deepening red. Tabletop games can record a level too.
- **Randomisers** for hero and villain on Quick Game, for the deck viewer, and
  one for each aspect dropdown. The hero draw shuffles heroes rather than
  decks, so a hero you have twelve netdecks for is no likelier than one you
  have a single deck for, and it prefers a synced deck over the precon.
- **Play this deck**, from the deck viewer straight to a set-up Quick Game.
- **A BG Stats location setting.** Left empty, BG Stats files plays under the
  app's name rather than leaving the field blank, so every play was landing
  somewhere that is not a place.
- **The campaign deck picker caught up with Quick Game's**: the filter bar,
  the aspect deck source, and the hero randomiser, from the same modules rather
  than a second copy that could drift. Aspect decks are frozen for the run the
  way MarvelCDB decks already were, because a campaign persists its hero as a
  deck file and an aspect deck is not one until it is written.
- **The difficulty controls stopped overlapping.** Each carried its own bottom
  margin, so the gap between any two depended on which happened to be last, and
  putting Heroic after Expert left them touching. The section spaces its own
  children now.
- **The README is this fork's own** rather than an edit of the one upstream:
  what the project is, who it came from, what it is for, and where your data
  lives — including that the MarvelCDB deck ID list is held by the browser and
  is in no server-side backup.

## Version 0.7.5 — “Cerebro” (2026-09-07)

Two features about knowing your own deck, and the diagnostics that today's
debugging said were missing.

- **Deck tracker.** A Deck button beside Log opens the decklist mid-game: every
  card that started in the deck, how many are left, and the ones that have all
  come out dimmed rather than removed, so the list keeps its shape all game.
  Hovering a row shows the card. Sorted by cost, and that is a rule rather than
  a preference — the engine sends the player deck to the client in real order,
  so a tracker that displayed it would hand you information the game means you
  not to have. Dismissed with the close in its corner or with Escape, without
  reaching back to the side bar.

- **Mulligan advice from the deck's author.** MarvelCDB descriptions often say
  what to keep in an opening hand, and the author knows what their deck is
  trying to do better than anything here could infer. The cards they name are
  shown at the top of the tracker with their own sentence beneath, and the ones
  already in your hand picked out. Finding it is the whole problem: across a
  96-deck collection, 33 descriptions mention the opening hand and only one put
  a heading on it, so the extraction follows the card links authors leave, the
  absolute form of those links, and — where they linked nothing — card names
  written in prose, matched only against cards the deck actually holds.
  Thirty-one of ninety-six decks yield advice this way.

- **A ranking for the rest.** The other three decks in four, and every precon
  and aspect deck, get five cards ranked from what the deck is made of, under a
  heading that says so rather than borrowing the author's authority. The
  weights are measured, not invented, and the measurement was worth doing: cost
  does not predict at all — flat across the curve, and the cards authors name
  cost more than average — while plain resources score 0.17 and allies 0.42.
  What authors dig for is the engine: an Upgrade or Support, often one they run
  three of. Leave-one-deck-out, the top five catches about a third of what an
  author would have named against a sixth by chance. Real, and modest, which is
  why it is never presented as somebody's advice.

- **Both in the deck viewer**, from the same function the table uses, so the two
  can never disagree about which kind of claim they are making.

- **Deck folders and the game history database log their absolute paths at
  startup.** A relative `./statistics.sqlite3` reads the same whether or not the
  volume beneath it is mounted, and a missing or misdirected mount is invisible
  from inside the container until it presents as data loss much later.

## Version 0.7.4.2 — “Cerebro” (2026-09-07)

- The name plays are filed under in BG Stats is a setting rather than a prompt.
  BG Stats matches that name to one of its own players once and remembers the
  match, so it has to stay the same between plays — a value that matters across
  sessions belongs somewhere it can be seen and corrected. It sits beside the
  MarvelCDB deck IDs and saves as it is typed. The storage key is unchanged, so
  a name already given to the prompt is already in the field, and with nothing
  set a play is filed under "Me" rather than asking.

## Version 0.7.4.1 — “Cerebro” (2026-09-07)

Start page presentation.

- New wallpaper, and the file is no longer named after the edition: it is
  `background.webp`, referenced by the route that serves it and the six
  stylesheets and pages that ask for it.
- The wallpaper ships in `public/` rather than `assets/textures/`. `assets` is
  a bind mount in the Docker deployment and a mount shadows whatever the image
  was built with, so a wallpaper kept there could be correct in the image and
  still not be the file being served. It is app chrome rather than something the
  player owns, and did not belong in that volume.
- The start page no longer carries a "Ronin Edition" heading. The edition is
  already in the page title and in the release label directly underneath, so it
  appeared three times in as many lines. The test now asserts it is absent, so
  it cannot drift back unnoticed.

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
