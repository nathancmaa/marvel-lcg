// Every key the game table already answers to.
//
// Here rather than in window.ts because two places need it: the table, which
// binds them, and the settings page, which has to say "that one is taken"
// before somebody assigns it to something else. A list that lives next to
// only one of those goes stale against the other.

export type BoundKey = {
    key: string;
    /** Held with ctrl, which makes a bare key of the same letter free. */
    ctrl?: boolean;
    does: string;
};

export const BOUND_KEYS: readonly BoundKey[] = [
    {key: 'Enter', does: 'OK'},
    {key: 'Escape', does: 'cancel, or close the log'},
    {key: 'Tab', does: 'open the log'},
    {key: ' ', does: 'pause'},
    {key: 'Pause', does: 'pause'},
    {key: 'Backspace', does: 'run to the end'},
    {key: '+', does: 'step the replay'},
    {key: 'F1', does: 'focus player 1'},
    {key: 'F2', does: 'focus player 2'},
    {key: 'F3', does: 'focus player 3'},
    {key: 'F4', does: 'focus player 4'},
    {key: '1', does: 'open your deck'},
    {key: '2', does: 'open your discard pile'},
    {key: '3', does: 'open the additional deck'},
    {key: '4', does: 'open the additional discard pile'},
    {key: 'q', does: 'turn the previewed card left'},
    {key: 'e', does: 'turn the previewed card right'},
    {key: 'r', does: 'turn the previewed card right'},
    {key: 'f', does: 'flip the previewed card'},
    {key: 'ArrowLeft', does: 'step back, in a replay'},
    {key: 'ArrowRight', does: 'step forward, in a replay'},
    {key: 'Home', does: 'go to the start, in a replay'},
    {key: 'End', does: 'go to the end, in a replay'},
    {key: 's', ctrl: true, does: 'save to slot 0'},
    {key: 'z', ctrl: true, does: 'undo'},
    {key: 'y', ctrl: true, does: 'replay'},
    {key: 'q', ctrl: true, does: 'run to the end'},
    {key: 'e', ctrl: true, does: 'replay'},
];

/**
 * What a bare key already does, or null when it is free.
 *
 * Only bare keys: ctrl+z is undo, which leaves a bare z free, and saying
 * otherwise would rule out most of the keyboard for no reason.
 */
export function whatKeyDoes(key: string): string | null {
    if (!key) {
        return null;
    }
    const bound = BOUND_KEYS.find(
        (entry) => !entry.ctrl && entry.key.toLowerCase() === key.toLowerCase());
    return bound ? bound.does : null;
}
