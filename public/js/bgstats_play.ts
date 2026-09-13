// Handing a finished game to BG Stats.
//
// BG Stats takes a whole play as one url-encoded JSON payload on a deep link;
// there is no API and no key. Opening the link hands the play to the app, which
// shows its own import dialog so nothing is recorded without the player seeing
// it first.
//
// The shape below is BG Stats' own, and two of its fields happen to fit this
// game exactly: `role` is what a player was in the play, which is the hero, and
// `board` is the board or variant, which is the scenario.

const BGSTATS_URL = 'https://app.bgstatsapp.com/createPlay.html';

/** Marvel Champions: The Card Game on BoardGameGeek. */
const MARVEL_CHAMPIONS_BGG_ID = 285774;

/**
 * Stable ids, because BG Stats remembers what the player matched them to.
 *
 * The game and the player each only have to be matched once, and only if these
 * do not change between plays -- so they are constants rather than anything
 * derived from a particular game.
 */
// BG Stats remembers which of its own games and players these map to, keyed on
// these ids, so changing one asks for that match to be made again. Renamed
// while nothing had yet been imported under the old ones and the match had
// never been made; they are not free to change once plays exist.
const SOURCE_GAME_ID = 'marvel-champions-digital';
const SOURCE_PLAYER_ID = 'marvel-champions-digital-player';
// What BG Stats shows as the source of these plays, and -- unless a location
// is set -- the location it files them under too. The edition name was dropped
// from the app's own chrome, and there is no reason for BG Stats to be the last
// place carrying it.
const SOURCE_NAME = 'Marvel Champions Digital';
// BG Stats' own separator for several roles in one field: a fullwidth
// solidus, which the app splits on. The history sends the seats joined by it.
const ROLE_SEPARATOR = '／';

export type BgStatsGame = {
    id: number;
    finished_at: string;
    hero_name: string;
    hero_code: string;
    villain_name: string;
    villain_code: string;
    expert: number;
    result: 'win'|'loss'|'unknown'|'abandoned';
    rounds: number|null;
    playtime_seconds: number|null;
    deck_name: string;
    notes: string;
    // Every seat of a two-handed game, joined by ROLE_SEPARATOR, in seat
    // order; absent or empty on a game recorded before seats were kept.
    seats?: number;
    heroes?: string|null;
    decks?: string|null;
};

/**
 * The play's end as `yyyy-MM-dd HH:mm:ss`, in this device's local time.
 *
 * The deep-link documentation says UTC. The app files what it is given as
 * local time regardless -- a play sent as 22:02 UTC came back out of the
 * app's own export as 22:02 beside an entry time of 15:02 -- so a play
 * sent in UTC sits hours late in the list. Local is what it wants, and
 * the device the link is opened on is the one whose clock counts.
 */
function playDate(finishedAt: string): string {
    const when = new Date(finishedAt);
    if (Number.isNaN(when.getTime())) {
        return '';
    }
    const two = (value: number): string => String(value).padStart(2, '0');
    return `${when.getFullYear()}-${two(when.getMonth() + 1)}-${two(when.getDate())}`
        + ` ${two(when.getHours())}:${two(when.getMinutes())}:${two(when.getSeconds())}`;
}

export function buildBgStatsPlay(
    game: BgStatsGame,
    playerName: string,
    location: string = '',
): unknown {
    const comments: string[] = [game.expert ? 'Expert' : 'Standard'];
    if (game.rounds) {
        comments.push(`${game.rounds} rounds`);
    }
    if ((game.seats ?? 0) > 1) {
        comments.push(`${game.seats}-handed`);
    }
    const decks = game.decks ? game.decks.split(ROLE_SEPARATOR) : [game.deck_name];
    for (const deck of decks) {
        if (deck.trim()) {
            comments.push(deck.trim());
        }
    }
    if (game.notes) {
        comments.push(game.notes);
    }

    const play: Record<string, unknown> = {
        sourceName: SOURCE_NAME,
        sourcePlayId: String(game.id),
        playDate: playDate(game.finished_at),
        // Kept short on purpose: the whole payload travels in a URL.
        comments: comments.join(' · ').slice(0, 400),
        board: game.villain_name,
        // Always named: the docs say an omitted location falls back to the
        // source name, but the app files such plays under "No location".
        location: location.trim() || SOURCE_NAME,
        game: {
            name: 'Marvel Champions: The Card Game',
            sourceGameId: SOURCE_GAME_ID,
            bggId: MARVEL_CHAMPIONS_BGG_ID,
            highestWins: true,
            // Win or loss, never a score.
            noPoints: true,
        },
        players: [{
            name: playerName,
            sourcePlayerId: SOURCE_PLAYER_ID,
            startPlayer: true,
            winner: game.result === 'win',
            // The hero, or both heroes of a two-handed game.
            role: game.heroes || game.hero_name,
        }],
    };

    const minutes = game.playtime_seconds === null
        ? null
        : Math.round(game.playtime_seconds / 60);
    if (minutes !== null && minutes > 0) {
        play.durationMin = minutes;
    }
    return play;
}

export function bgStatsPlayUrl(
    game: BgStatsGame,
    playerName: string,
    location: string = '',
): string {
    const data = encodeURIComponent(
        JSON.stringify(buildBgStatsPlay(game, playerName, location)));
    return `${BGSTATS_URL}?data=${data}`;
}

/**
 * The same link on the app's own scheme, which is what the web page above
 * rewrites its "click here" to: `https://` becomes `bgstats://`.
 */
export function bgStatsAppUrl(
    game: BgStatsGame,
    playerName: string,
    location: string = '',
): string {
    return 'bgstats' + bgStatsPlayUrl(game, playerName, location).slice('https'.length);
}

/**
 * Hand a play to BG Stats without leaving this page.
 *
 * The app's scheme is tried first, in place: a browser passes it to the app
 * and stays where it is, so there is no blank tab to close afterwards. Only
 * if nothing takes it -- the page still has focus a moment later, which is
 * the web page's own test -- does the https link open in a new tab, where it
 * explains how to get the app.
 */
export function sendToBgStats(
    game: BgStatsGame,
    playerName: string,
    location: string = '',
): void {
    let handedOff = false;
    const onBlur = () => { handedOff = true; };
    window.addEventListener('blur', onBlur, {once: true});
    window.location.href = bgStatsAppUrl(game, playerName, location);
    window.setTimeout(() => {
        window.removeEventListener('blur', onBlur);
        if (!handedOff && document.visibilityState === 'visible') {
            window.open(bgStatsPlayUrl(game, playerName, location), '_blank', 'noopener');
        }
    }, 1500);
}

/**
 * Whether this game is worth sending.
 *
 * An unfinished or abandoned game has no result for BG Stats to record, and it
 * would arrive there as a loss.
 */
export function canPushToBgStats(game: BgStatsGame): boolean {
    return game.result === 'win' || game.result === 'loss';
}
