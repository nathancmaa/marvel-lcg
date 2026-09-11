export const ANIMATION_TIME_MIN = 0.1
export const ANIMATION_TIME_MAX = 1.5
export const ANIMATION_TIME_DEFAULT = 0.2

const animationTimeKey = 'marvel_lcg_animation_time'
const autoSaveReplaysKey = 'marvel_lcg_autosave_replays'
const marvelCdbDeckIdsKey = 'marvel_lcg_marvelcdb_deck_ids'
const bgStatsPlayerKey = 'marvel_lcg_bgstats_player'
const bgStatsLocationKey = 'marvel_lcg_bgstats_location'
const twoHandedKey = 'marvel_lcg_two_handed_solo'
const confirmKeyKey = 'marvel_lcg_confirm_key'
const denyKeyKey = 'marvel_lcg_deny_key'
const undoKeyKey = 'marvel_lcg_undo_key'
const optionKeysKey = 'marvel_lcg_option_keys'

/**
 * The keys that take the options on screen, by position.
 *
 * The home row, left to right, because the row below it holds the three
 * answers that are always available -- OK, cancel and undo -- and a choice
 * between named options is the other thing the table asks for often. Nine
 * because that is more options than an ask has ever put up at once.
 */
export const DEFAULT_OPTION_KEYS: readonly string[] =
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l']

const cardScaleKey = 'marvel_lcg_card_scale'

/**
 * Card size, as a percentage of what the stylesheet asks for.
 *
 * In steps, not continuously: the rows a card sits in are pinned at fixed
 * stage coordinates, so every size that makes a card taller needs its own
 * set of those, and a handful of sizes is a handful of tables rather than a
 * function of a slider position.
 *
 * The maximum is 100 for now. Smaller cards only ever leave more room, both
 * across a row and between rows; larger ones run into the 4 to 24 pixels of
 * slack between one row and the next, which is the work that has not been
 * done yet.
 */
export const CARD_SCALE_MIN = 50
export const CARD_SCALE_MAX = 100
export const CARD_SCALE_STEP = 5
export const CARD_SCALE_DEFAULT = 100

function readStorage(key: string): string|null {
    try {
        return localStorage.getItem(key)
    } catch( error ) {
        console.warn(`Could not read browser setting ${key}`, error)
        return null
    }
}

function writeStorage(key: string, value: string) {
    try {
        localStorage.setItem(key, value)
    } catch( error ) {
        console.warn(`Could not save browser setting ${key}`, error)
    }
}

export class UserSettings {
    static getAnimationTime(): number {
        const value = Number(readStorage(animationTimeKey))
        if( Number.isFinite(value) && value >= ANIMATION_TIME_MIN && value <= ANIMATION_TIME_MAX ) {
            return value
        }
        return ANIMATION_TIME_DEFAULT
    }

    static setAnimationTime(value: number) {
        const normalizedValue = Math.min(
            ANIMATION_TIME_MAX,
            Math.max(ANIMATION_TIME_MIN, value),
        )
        writeStorage(animationTimeKey, normalizedValue.toString())
    }

    static getAutoSaveReplays(): boolean {
        return readStorage(autoSaveReplaysKey) === 'true'
    }

    static setAutoSaveReplays(enabled: boolean) {
        writeStorage(autoSaveReplaysKey, enabled.toString())
    }

    static getMarvelCdbDeckIds(): string {
        return readStorage(marvelCdbDeckIdsKey)?.trim() ?? ''
    }

    static setMarvelCdbDeckIds(deckIds: string) {
        writeStorage(marvelCdbDeckIdsKey, deckIds.trim())
    }

    /**
     * The name a play is filed under when it is pushed to BG Stats.
     *
     * BG Stats matches this to one of its own players the first time and
     * remembers the match, so it only has to be recognisable rather than
     * exact -- but it does have to stay the same, which is why it is a
     * setting rather than something asked for per play.
     */
    static getBgStatsPlayerName(): string {
        return readStorage(bgStatsPlayerKey)?.trim() ?? ''
    }

    static setBgStatsPlayerName(name: string) {
        writeStorage(bgStatsPlayerKey, name.trim())
    }

    /**
     * Where BG Stats files these plays.
     *
     * Left empty, BG Stats does not leave the location blank -- it files the
     * play under the source name, so every play from here lands somewhere
     * called "Marvel Champions Digital" whether or not that is a place. This
     * is how you say it happened at home, or at a table, or anywhere real.
     */
    static getBgStatsLocation(): string {
        return readStorage(bgStatsLocationKey)?.trim() ?? ''
    }

    static setBgStatsLocation(location: string) {
        writeStorage(bgStatsLocationKey, location.trim())
    }

    /**
     * Whether Quick Game sets up one hero or two.
     *
     * Two-handed is one person playing both heroes from one screen, which the
     * engine has always supported -- the hot seat is upstream's, and this
     * fork only ever stopped offering a way in. Off by default, because one
     * hero against a villain is what this fork is for and the second picker
     * would otherwise be in the way of every game.
     */
    static getTwoHandedSolo(): boolean {
        return readStorage(twoHandedKey) === 'true'
    }

    static setTwoHandedSolo(enabled: boolean) {
        writeStorage(twoHandedKey, enabled.toString())
    }

    /**
     * A second key for OK, beside Enter.
     *
     * Enter and Escape both work and both sit under the hand that is not on
     * the mouse, which is what makes them slow: the answer to most prompts is
     * yes or no, and reaching for a corner of the keyboard to say it costs
     * more than the answer is worth. These are for a key under the fingers.
     *
     * Empty means the second key is off and only Enter and Escape answer.
     */
    static getConfirmKey(): string {
        return readStorage(confirmKeyKey) ?? 'z'
    }

    static setConfirmKey(key: string) {
        writeStorage(confirmKeyKey, key)
    }

    /** A second key for cancel or skip, beside Escape. */
    static getDenyKey(): string {
        return readStorage(denyKeyKey) ?? 'x'
    }

    static setDenyKey(key: string) {
        writeStorage(denyKeyKey, key)
    }

    /**
     * A bare key for undo, beside ctrl+z.
     *
     * Undo is the most pressed key at the table after the two answers, and it
     * was the only one of the three still needing both hands. Defaults to c,
     * which nothing else uses and which sits next to the z and x that answer.
     */
    static getUndoKey(): string {
        return readStorage(undoKeyKey) ?? 'c'
    }

    static setUndoKey(key: string) {
        writeStorage(undoKeyKey, key)
    }

    /**
     * One key per option position. An empty string leaves that position
     * without one, which is how a position is turned off.
     */
    static getOptionKeys(): string[] {
        const stored = readStorage(optionKeysKey)
        if( stored === null ) {
            return [...DEFAULT_OPTION_KEYS]
        }
        try {
            const keys = JSON.parse(stored) as unknown
            if( !Array.isArray(keys) ) {
                return [...DEFAULT_OPTION_KEYS]
            }
            // Padded to the full length so a short or hand-edited list cannot
            // leave later positions reading undefined.
            return DEFAULT_OPTION_KEYS.map(
                (_, at) => typeof keys[at] === 'string' ? keys[at] as string : '')
        } catch( error ) {
            console.warn('Could not read the option keys', error)
            return [...DEFAULT_OPTION_KEYS]
        }
    }

    static setOptionKeys(keys: readonly string[]) {
        writeStorage(optionKeysKey, JSON.stringify(keys))
    }

    /** Card size as a percentage, snapped to a step the layout has a table for. */
    static getCardScale(): number {
        // Tested for null before converting: Number(null) is 0, which is
        // finite, so a missing setting would otherwise clamp to the minimum
        // and every new browser would open at the smallest card.
        const stored = readStorage(cardScaleKey)
        const value = stored === null ? NaN : Number(stored)
        if( !Number.isFinite(value) ) {
            return CARD_SCALE_DEFAULT
        }
        const snapped = Math.round(value / CARD_SCALE_STEP) * CARD_SCALE_STEP
        return Math.min(CARD_SCALE_MAX, Math.max(CARD_SCALE_MIN, snapped))
    }

    static setCardScale(percent: number) {
        writeStorage(cardScaleKey, String(percent))
    }
}
