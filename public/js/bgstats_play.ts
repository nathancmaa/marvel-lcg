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
const SOURCE_GAME_ID = 'ronin-marvel-champions';
const SOURCE_PLAYER_ID = 'ronin-solo-player';
const SOURCE_NAME = 'Marvel Champions Digital: Ronin Edition';

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
};

/** BG Stats wants UTC as `yyyy-MM-dd HH:mm:ss`. */
function playDate(finishedAt: string): string {
    const when = new Date(finishedAt);
    if (Number.isNaN(when.getTime())) {
        return '';
    }
    return when.toISOString().slice(0, 19).replace('T', ' ');
}

export function buildBgStatsPlay(game: BgStatsGame, playerName: string): unknown {
    const comments: string[] = [game.expert ? 'Expert' : 'Standard'];
    if (game.rounds) {
        comments.push(`${game.rounds} rounds`);
    }
    if (game.deck_name) {
        comments.push(game.deck_name);
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
            role: game.hero_name,
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

export function bgStatsPlayUrl(game: BgStatsGame, playerName: string): string {
    const data = encodeURIComponent(JSON.stringify(buildBgStatsPlay(game, playerName)));
    return `${BGSTATS_URL}?data=${data}`;
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
