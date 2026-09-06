// The prebuilt aspect decks: aspect and basic cards only, no hero cards.
//
// They exist because a deck on MarvelCDB is always attached to a hero, so one
// cannot be loaded and then paired with somebody else. These carry the card
// list alone, which is combined with whichever hero is chosen in the picker.
//
// Several are trait-locked -- X-Men, Web-Warrior, Guardian, Avenger -- and some
// name cards to remove for a hero that does not fit. None of that is enforced
// here; the deck's own notes say so and the choice is the player's.

export type AspectDeck = {
    id: string;
    name: string;
    aspect: string;
    url: string;
    description: string;
    player_deck: string[];
};

type AspectDeckFile = {
    source?: string;
    source_url?: string;
    decks: AspectDeck[];
};

export type AspectDeckPicker = {
    /** The deck currently chosen, or null while none is. */
    getDeck(): AspectDeck | null;
    /** Load the catalogue and fill the dropdown. Safe to call once. */
    load(): Promise<void>;
};

const STORAGE_KEY = 'marvel_lcg_solo_aspect_deck';

export function createAspectDeckPicker(options: {
    onChange: () => void;
}): AspectDeckPicker {
    const select = document.querySelector<HTMLSelectElement>('#aspect-deck');
    const description = document.querySelector<HTMLElement>('#aspect-description');
    const sourceLink = document.querySelector<HTMLAnchorElement>('#aspect-source-link');

    let decks: AspectDeck[] = [];
    let chosen: AspectDeck | null = null;

    function show(deck: AspectDeck | null): void {
        chosen = deck;
        if (description) {
            description.textContent = deck ? deck.description : '';
        }
        options.onChange();
    }

    function remember(id: string): void {
        try {
            localStorage.setItem(STORAGE_KEY, id);
        } catch {
            // Persistence is a convenience; losing it is not worth an error.
        }
    }

    select?.addEventListener('change', () => {
        const deck = decks.find((item) => item.id === select.value) ?? null;
        remember(select.value);
        show(deck);
    });

    return {
        getDeck: () => chosen,

        async load(): Promise<void> {
            if (!select) {
                return;
            }
            try {
                const response = await fetch('/get_aspect_decks_json?');
                if (!response.ok) {
                    throw new Error(`${response.status} ${response.statusText}`);
                }
                const file = await response.json() as AspectDeckFile;
                decks = Array.isArray(file.decks) ? file.decks : [];
                if (sourceLink && file.source_url) {
                    sourceLink.href = file.source_url;
                }
            } catch (error) {
                console.warn('Could not load the aspect decks', error);
                select.replaceChildren(new Option('Aspect decks unavailable', ''));
                select.disabled = true;
                return;
            }

            select.replaceChildren();
            select.appendChild(new Option('Choose an aspect deck…', ''));
            // Grouped by aspect, which is how anyone looking for one thinks
            // about them.
            const byAspect = new Map<string, AspectDeck[]>();
            for (const deck of decks) {
                const group = byAspect.get(deck.aspect);
                if (group) {
                    group.push(deck);
                } else {
                    byAspect.set(deck.aspect, [deck]);
                }
            }
            for (const aspect of [...byAspect.keys()].sort()) {
                const group = document.createElement('optgroup');
                group.label = aspect;
                for (const deck of byAspect.get(aspect)!) {
                    group.appendChild(new Option(deck.name, deck.id));
                }
                select.appendChild(group);
            }
            select.disabled = false;

            let saved = '';
            try {
                saved = localStorage.getItem(STORAGE_KEY) ?? '';
            } catch {
                saved = '';
            }
            const remembered = decks.find((deck) => deck.id === saved);
            if (remembered) {
                select.value = remembered.id;
                show(remembered);
            }
        },
    };
}
