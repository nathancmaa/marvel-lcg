// The prebuilt universal decks: one per hero, from the same geeklist as the
// aspect decks.
//
// The difference is who they belong to. An aspect deck holds no hero cards and
// pairs with anybody, so it is chosen from a list. A universal deck was built
// for one hero, so there is nothing to choose: pick the hero and the deck is
// already decided. That is why this has no dropdown of its own.
//
// The list's premise is a full collection holding every deck at once with no
// card moved between them, which matters at a table and not here. What it
// leaves behind is a ready-made deck for each hero, which is the useful part.

export type UniversalDeck = {
    id: string;
    hero: string;
    hero_name: string;
    name: string;
    aspect: string;
    player_deck: string[];
};

type UniversalDeckFile = {
    source?: string;
    source_url?: string;
    decks: UniversalDeck[];
};

export type UniversalDeckPicker = {
    /** The deck built for this hero, or null when the list has none. */
    getDeckFor(heroId: string): UniversalDeck | null;
    /** Describe the deck for this hero in the panel. */
    show(heroId: string, heroName: string): void;
    /** Load the catalogue. Safe to call once. */
    load(): Promise<void>;
};

export function createUniversalDeckPicker(options: {
    onChange: () => void;
}): UniversalDeckPicker {
    const summary = document.querySelector<HTMLElement>('#universal-summary');
    const sourceLink = document.querySelector<HTMLAnchorElement>('#universal-source-link');

    let decks = new Map<string, UniversalDeck>();
    let loaded = false;

    function getDeckFor(heroId: string): UniversalDeck | null {
        return decks.get(heroId) ?? null;
    }

    return {
        getDeckFor,

        show(heroId: string, heroName: string): void {
            if (!summary) {
                return;
            }
            if (!loaded) {
                summary.textContent = 'Loading the universal decks…';
                return;
            }
            const deck = heroId ? getDeckFor(heroId) : null;
            if (deck) {
                summary.textContent = `${deck.name} · ${deck.aspect} · 25 cards`;
                summary.classList.remove('missing');
                return;
            }
            // Said plainly, because the reason is never the player's doing:
            // the list has no deck for this hero, or the one it has names
            // cards this installation cannot play.
            summary.textContent = heroId
                ? `There is no universal deck for ${heroName}. Pick another hero, or another deck.`
                : 'Choose a hero to see their universal deck.';
            summary.classList.add('missing');
        },

        async load(): Promise<void> {
            try {
                const response = await fetch('/get_universal_decks_json?');
                if (!response.ok) {
                    throw new Error(`${response.status} ${response.statusText}`);
                }
                const file = await response.json() as UniversalDeckFile;
                decks = new Map(
                    (Array.isArray(file.decks) ? file.decks : [])
                        .map((deck) => [deck.hero, deck]),
                );
                if (sourceLink && file.source_url) {
                    sourceLink.href = file.source_url;
                }
            } catch (error) {
                console.warn('Could not load the universal decks', error);
                decks = new Map();
            }
            loaded = true;
            options.onChange();
        },
    };
}
