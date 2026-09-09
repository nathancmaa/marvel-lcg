// The one ladder for "how hard have I beaten this", shared by every page that
// draws it.
//
// Game history records the best clear for a pairing as a single number:
// 0 never, 1 Standard, 2 Expert, 3 and up Heroic at (value - 2). The coverage
// grid on the statistics page and the scenario tiles on Quick Game both colour
// by it, and two copies of a ladder is exactly the kind of thing that drifts
// apart one pack at a time.

/** The class carrying the colour for a clear, or '' for one never beaten. */
export function beatenClass(beaten: number): string {
    return beaten >= 3 ? `beaten-heroic-${Math.min(beaten - 2, 4)}`
        : beaten === 2 ? 'beaten-expert'
        : beaten === 1 ? 'beaten-standard'
        : '';
}

/** How that clear reads in a tooltip. */
export function beatenLabel(beaten: number): string {
    return beaten >= 3 ? `best clear: Heroic ${beaten - 2}`
        : beaten === 2 ? 'best clear: Expert'
        : beaten === 1 ? 'best clear: Standard'
        : 'not beaten yet';
}
