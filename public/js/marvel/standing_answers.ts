// Cards you have told the game to activate without asking, in the order they
// should go.
//
// Marvel Champions offers every response that triggered at once as one choice,
// and picking one asks again with what is left. So "activate this without
// asking" is only half an instruction: when two marked cards trigger together
// -- Mission Leader drawing a card and Graymalkin readying, both off the same
// defeated side scheme -- something has to say which goes first. That is what
// the order is. Rare that it matters, common enough that stopping to ask
// whenever two are live would give most of the saving straight back.
//
// The list belongs to the game being played, not to the installation. A
// standing answer is a decision about this deck against this villain, and
// carrying it into the next game is how a card fires in a game you never meant
// it to. It survives a page refresh and nothing else.

const STORAGE_KEY = 'marvel_lcg_standing_answers';

/** A card that answers for itself, and the name to show it under. */
export type StandingAnswer = {
    card_id: string;
    /** Kept because the card may have left play by the time the list is read. */
    name: string;
};

type Stored = {
    /** The game these belong to; a different one starts an empty list. */
    game_id: number;
    /** Highest priority first. */
    order: StandingAnswer[];
};

export class StandingAnswers {
    private static game_id = -1;
    private static order: StandingAnswer[] = [];
    private static listeners: Array<() => void> = [];

    /** Told which game is on the table. A new one empties the list. */
    static setGame(game_id: number): void {
        if( StandingAnswers.game_id === game_id ) {
            return;
        }
        StandingAnswers.game_id = game_id;
        const stored = StandingAnswers.read();
        StandingAnswers.order = stored && stored.game_id === game_id
            ? [...stored.order]
            : [];
        StandingAnswers.save();
        StandingAnswers.announce();
    }

    private static read(): Stored | null {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) as Stored : null;
        } catch {
            // A hand-edited or cleared store should never stop a game.
            return null;
        }
    }

    private static save(): void {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                game_id: StandingAnswers.game_id,
                order: StandingAnswers.order,
            }));
        } catch {
            // Losing the list costs the marks, not the game.
        }
    }

    private static announce(): void {
        for( const listener of StandingAnswers.listeners ) {
            listener();
        }
    }

    /** Redraw whatever shows the list when it changes. */
    static onChanged(listener: () => void): void {
        StandingAnswers.listeners.push(listener);
    }

    private static indexOf(card_id: string): number {
        return StandingAnswers.order.findIndex(
            (entry) => entry.card_id === card_id);
    }

    static has(card_id: string): boolean {
        return StandingAnswers.indexOf(card_id) >= 0;
    }

    static list(): readonly StandingAnswer[] {
        return StandingAnswers.order;
    }

    /** Where a card sits, or a number past the end when it is not on the list. */
    static rankOf(card_id: string): number {
        const at = StandingAnswers.indexOf(card_id);
        return at < 0 ? Number.MAX_SAFE_INTEGER : at;
    }

    /** Mark a card, or unmark it, and report which it now is. */
    static toggle(card_id: string, name: string): boolean {
        if( StandingAnswers.has(card_id) ) {
            StandingAnswers.remove(card_id);
            return false;
        }
        // The bottom, because a card marked later has had every card above it
        // already answered for; putting it on top would silently reorder the
        // answers you already settled.
        StandingAnswers.order.push({card_id, name});
        StandingAnswers.save();
        StandingAnswers.announce();
        return true;
    }

    static remove(card_id: string): void {
        const at = StandingAnswers.indexOf(card_id);
        if( at < 0 ) {
            return;
        }
        StandingAnswers.order.splice(at, 1);
        StandingAnswers.save();
        StandingAnswers.announce();
    }

    /** Move a card one place up or down the order. */
    static move(card_id: string, by: -1 | 1): void {
        const at = StandingAnswers.indexOf(card_id);
        const to = at + by;
        if( at < 0 || to < 0 || to >= StandingAnswers.order.length ) {
            return;
        }
        const [entry] = StandingAnswers.order.splice(at, 1);
        StandingAnswers.order.splice(to, 0, entry);
        StandingAnswers.save();
        StandingAnswers.announce();
    }

    static clear(): void {
        StandingAnswers.order = [];
        StandingAnswers.save();
        StandingAnswers.announce();
    }
}
