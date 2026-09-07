export const ANIMATION_TIME_MIN = 0.1
export const ANIMATION_TIME_MAX = 1.5
export const ANIMATION_TIME_DEFAULT = 0.2

const animationTimeKey = 'marvel_lcg_animation_time'
const autoSaveReplaysKey = 'marvel_lcg_autosave_replays'
const marvelCdbDeckIdsKey = 'marvel_lcg_marvelcdb_deck_ids'
const bgStatsPlayerKey = 'marvel_lcg_bgstats_player'
const bgStatsLocationKey = 'marvel_lcg_bgstats_location'

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
}
