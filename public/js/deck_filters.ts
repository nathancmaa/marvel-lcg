// Filtering, sorting and grouping for the hero deck picker.
//
// This lives outside solo.ts on purpose. solo.ts is the most frequently
// changed file in the repository, so keeping the deck-browsing logic here
// leaves only a couple of call sites to reconcile when merging upstream.
//
// The module owns its own controls markup as well, so solo.html needs no
// changes -- the deck list is JavaScript-generated already.

export type DeckFilterData = {
    name: string;
    deck_name?: string;
    player_deck?: string[];
    metadata?: Record<string, string>;
};

export type DeckFilterChoice = {
    id: string;
    isUserDeck: boolean;
    isResolvedMarvelCdb?: boolean;
    data: DeckFilterData;
};

type SortMode = 'deck' | 'hero' | 'aspect' | 'updated';

type ControlState = {
    heroId: string;
    sort: SortMode;
    hidePrecons: boolean;
    groupByHero: boolean;
};

const STORAGE_KEY = 'marvel_lcg_solo_deck_filters';

// Card classes as they appear in cards.json `desc.Class`. Anything outside
// this set (Hero, Basic, Campaign, Encounter, or absent) says nothing about
// which aspect a deck plays. `'Pool` is Deadpool's own class -- his decks
// contain no standard aspect cards at all, so without it they would all be
// reported as having no aspect.
const ASPECT_CLASSES: ReadonlySet<string> = new Set([
    'Aggression', 'Justice', 'Leadership', 'Protection', "'Pool",
]);

// A handful of cards carry two classes joined by a semicolon, e.g.
// `Hero;Aggression`, so the field is split rather than compared whole.
const CLASS_SEPARATOR = ';';

const ASPECT_NONE = 'No aspect';

const SORT_LABELS: ReadonlyArray<readonly [SortMode, string]> = [
    ['deck', 'Deck name'],
    ['hero', 'Hero'],
    ['aspect', 'Aspect'],
    ['updated', 'Recently updated'],
];

const DEFAULT_STATE: ControlState = {
    heroId: '',
    sort: 'deck',
    hidePrecons: false,
    groupByHero: false,
};

function readState(): ControlState {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return {...DEFAULT_STATE};
        }
        const parsed = JSON.parse(raw) as Partial<ControlState>;
        const sort = SORT_LABELS.some(([mode]) => mode === parsed.sort)
            ? parsed.sort as SortMode
            : DEFAULT_STATE.sort;
        return {
            heroId: typeof parsed.heroId === 'string' ? parsed.heroId : '',
            sort,
            hidePrecons: parsed.hidePrecons === true,
            groupByHero: parsed.groupByHero === true,
        };
    } catch {
        // A private window, cleared storage, or a hand-edited value should
        // never stop the picker from rendering.
        return {...DEFAULT_STATE};
    }
}

function writeState(state: ControlState): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
        // Persistence is a convenience; losing it is not worth an error.
    }
}

function deckNameOf(choice: DeckFilterChoice): string {
    return choice.data.deck_name ?? choice.data.name;
}

function heroNameOf(choice: DeckFilterChoice): string {
    return choice.data.name;
}

function compareText(left: string, right: string): number {
    return left.localeCompare(right, undefined, {sensitivity: 'base', numeric: true});
}

/** Last-updated timestamp for MarvelCDB decks; '' for everything else. */
function updatedAtOf(choice: DeckFilterChoice): string {
    return choice.data.metadata?.date_update ?? '';
}

// ---------------------------------------------------------------------------
// Aspect lookup
//
// Aspect is not stored on a deck. It is derived from the cards it contains, so
// it needs the card database -- which is ~2.4 MB and irrelevant to every other
// sort mode. It is therefore fetched only when aspect sorting is first used,
// and cached for the life of the page.
// ---------------------------------------------------------------------------

type CardEntry = {card_id?: string; desc?: unknown};

let cardClassPromise: Promise<Map<string, string>> | null = null;

async function loadCardClasses(): Promise<Map<string, string>> {
    if (!cardClassPromise) {
        cardClassPromise = (async () => {
            const response = await fetch('/get_cards_json?');
            if (!response.ok) {
                throw new Error(`get_cards_json returned ${response.status}`);
            }
            const packs = await response.json() as Record<string, unknown>;
            const classes = new Map<string, string>();
            for (const cards of Object.values(packs)) {
                if (!Array.isArray(cards)) {
                    continue;
                }
                for (const card of cards as CardEntry[]) {
                    const desc = card?.desc;
                    if (!card?.card_id || typeof desc !== 'object' || desc === null) {
                        continue;
                    }
                    const cardClass = (desc as Record<string, string>).Class;
                    if (typeof cardClass === 'string') {
                        classes.set(card.card_id, cardClass);
                    }
                }
            }
            return classes;
        })().catch((error) => {
            // Allow a later attempt to retry rather than caching the failure.
            cardClassPromise = null;
            throw error;
        });
    }
    return cardClassPromise;
}

/** The aspect a deck plays, by majority of its aspect-restricted cards. */
function aspectOf(choice: DeckFilterChoice, classes: Map<string, string>): string {
    const tally = new Map<string, number>();
    for (const cardId of choice.data.player_deck ?? []) {
        const cardClass = classes.get(cardId);
        if (!cardClass) {
            continue;
        }
        for (const part of cardClass.split(CLASS_SEPARATOR)) {
            if (ASPECT_CLASSES.has(part)) {
                tally.set(part, (tally.get(part) ?? 0) + 1);
            }
        }
    }
    let best = ASPECT_NONE;
    let bestCount = 0;
    for (const [aspect, count] of tally) {
        // Ties break alphabetically so the label is stable between renders.
        if (count > bestCount || (count === bestCount && compareText(aspect, best) < 0)) {
            best = aspect;
            bestCount = count;
        }
    }
    return best;
}

// ---------------------------------------------------------------------------

export type DeckFiltersOptions<T extends DeckFilterChoice> = {
    /** The `.choice-grid` the deck buttons are rendered into. */
    listHost: HTMLElement;
    /** Builds the button for one deck; owned by the caller. */
    createButton: (choice: T) => HTMLElement;
    /** Called after every re-render so the caller can restore selection state. */
    onRendered?: () => void;
};

export type DeckFilters<T extends DeckFilterChoice> = {
    /** Replace the deck list and redraw. */
    render(choices: T[]): void;
};

export function createDeckFilters<T extends DeckFilterChoice>(
    options: DeckFiltersOptions<T>,
): DeckFilters<T> {
    const {listHost, createButton, onRendered} = options;
    const state = readState();

    let source: T[] = [];
    let aspects: Map<string, string> | null = null;

    const bar = document.createElement('div');
    bar.className = 'deck-filters';
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', 'Deck list options');

    const heroSelect = document.createElement('select');
    heroSelect.className = 'deck-filter-select';
    heroSelect.id = 'deck-filter-hero';

    const heroLabel = document.createElement('label');
    heroLabel.className = 'deck-filter-field';
    heroLabel.htmlFor = heroSelect.id;
    heroLabel.append(labelText('Hero'), heroSelect);

    const sortSelect = document.createElement('select');
    sortSelect.className = 'deck-filter-select';
    sortSelect.id = 'deck-filter-sort';
    for (const [mode, label] of SORT_LABELS) {
        const option = document.createElement('option');
        option.value = mode;
        option.textContent = label;
        sortSelect.appendChild(option);
    }
    sortSelect.value = state.sort;

    const sortLabel = document.createElement('label');
    sortLabel.className = 'deck-filter-field';
    sortLabel.htmlFor = sortSelect.id;
    sortLabel.append(labelText('Sort by'), sortSelect);

    const groupToggle = createToggle('Group by hero', state.groupByHero);
    const preconToggle = createToggle('Hide precons', state.hidePrecons);

    const count = document.createElement('span');
    count.className = 'deck-filter-count';
    count.setAttribute('aria-live', 'polite');

    bar.append(heroLabel, sortLabel, groupToggle, preconToggle, count);
    listHost.parentElement?.insertBefore(bar, listHost);

    function labelText(text: string): HTMLSpanElement {
        const span = document.createElement('span');
        span.className = 'deck-filter-label';
        span.textContent = text;
        return span;
    }

    function createToggle(text: string, pressed: boolean): HTMLButtonElement {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'deck-filter-toggle';
        button.textContent = text;
        button.setAttribute('aria-pressed', String(pressed));
        button.classList.toggle('active', pressed);
        return button;
    }

    function setPressed(button: HTMLButtonElement, pressed: boolean): void {
        button.setAttribute('aria-pressed', String(pressed));
        button.classList.toggle('active', pressed);
    }

    function persist(): void {
        writeState(state);
    }

    /** Decks the controls apply to. A loaded MarvelCDB deck is pinned by
     *  solo.ts outside this list and must not be filtered away. */
    function browsable(): T[] {
        return source.filter((choice) => !choice.isResolvedMarvelCdb);
    }

    function refreshHeroOptions(): void {
        const heroes = [...new Set(browsable().map(heroNameOf))]
            .sort((left, right) => compareText(left, right));
        const previous = state.heroId;
        heroSelect.replaceChildren();

        const all = document.createElement('option');
        all.value = '';
        all.textContent = 'All heroes';
        heroSelect.appendChild(all);

        for (const hero of heroes) {
            const option = document.createElement('option');
            option.value = hero;
            option.textContent = hero;
            heroSelect.appendChild(option);
        }

        // A remembered hero that no longer has decks falls back to "All"
        // rather than leaving the picker mysteriously empty.
        if (previous && !heroes.includes(previous)) {
            state.heroId = '';
            persist();
        }
        heroSelect.value = state.heroId;
    }

    function applyFilters(choices: T[]): T[] {
        return choices.filter((choice) => {
            if (state.hidePrecons && !choice.isUserDeck) {
                return false;
            }
            if (state.heroId && heroNameOf(choice) !== state.heroId) {
                return false;
            }
            return true;
        });
    }

    function sortKey(choice: T): string {
        switch (state.sort) {
            case 'hero':
                return heroNameOf(choice);
            case 'aspect':
                return aspects ? aspectOf(choice, aspects) : '';
            case 'updated':
                return updatedAtOf(choice);
            default:
                return deckNameOf(choice);
        }
    }

    function applySort(choices: T[], separateSources = false): T[] {
        const sorted = [...choices];
        sorted.sort((left, right) => {
            // Ungrouped, the picker has always listed your own decks above the
            // precons. Keep that: sorting alphabetically across both would bury
            // a synced deck among 68 starter decks.
            if (separateSources && left.isUserDeck !== right.isUserDeck) {
                return left.isUserDeck ? -1 : 1;
            }
            // Newest first reads naturally for a recency sort; decks with no
            // timestamp (precons) sort last rather than leading with blanks.
            if (state.sort === 'updated') {
                const leftAt = updatedAtOf(left);
                const rightAt = updatedAtOf(right);
                if (leftAt !== rightAt) {
                    if (!leftAt) return 1;
                    if (!rightAt) return -1;
                    return rightAt.localeCompare(leftAt);
                }
            } else {
                const comparison = compareText(sortKey(left), sortKey(right));
                if (comparison !== 0) {
                    return comparison;
                }
            }
            return compareText(deckNameOf(left), deckNameOf(right))
                || compareText(left.id, right.id);
        });
        return sorted;
    }

    type Section = {label: string | null; items: T[]};

    function arrange(choices: T[]): Section[] {
        const filtered = applyFilters(choices);
        if (!state.groupByHero) {
            return [{label: null, items: applySort(filtered, true)}];
        }

        const groups = new Map<string, T[]>();
        for (const choice of filtered) {
            const hero = heroNameOf(choice);
            const bucket = groups.get(hero);
            if (bucket) {
                bucket.push(choice);
            } else {
                groups.set(hero, [choice]);
            }
        }
        return [...groups.keys()]
            .sort((left, right) => compareText(left, right))
            .map((hero) => ({label: hero, items: applySort(groups.get(hero)!)}));
    }

    function draw(): void {
        const sections = arrange(browsable());
        const total = sections.reduce((sum, section) => sum + section.items.length, 0);

        // solo.ts pins a loaded MarvelCDB deck by prepending it straight into
        // the list, outside anything this module tracks. Carry that element
        // across the redraw, or changing a filter would silently remove the
        // deck the player just loaded and still has selected.
        const pinned = listHost.querySelector('.resolved-marvelcdb-deck');
        listHost.replaceChildren();
        if (pinned) {
            listHost.appendChild(pinned);
        }
        for (const section of sections) {
            if (section.label !== null) {
                const heading = document.createElement('h3');
                heading.className = 'deck-group-heading';
                heading.textContent = `${section.label} (${section.items.length})`;
                listHost.appendChild(heading);
            }
            for (const choice of section.items) {
                listHost.appendChild(createButton(choice));
            }
        }

        if (total === 0 && browsable().length > 0) {
            const empty = document.createElement('p');
            empty.className = 'deck-filter-empty';
            empty.textContent = 'No decks match these options.';
            listHost.appendChild(empty);
        }

        const available = browsable().length;
        count.textContent = total === available
            ? `${total} deck${total === 1 ? '' : 's'}`
            : `${total} of ${available} decks`;

        onRendered?.();
    }

    async function ensureAspectsThenDraw(): Promise<void> {
        if (state.sort !== 'aspect' || aspects) {
            draw();
            return;
        }
        // The card database is large, so say something while it arrives.
        count.textContent = 'Loading card data…';
        try {
            aspects = await loadCardClasses();
        } catch (error) {
            console.warn('Could not load card data for aspect sorting', error);
            state.sort = 'deck';
            sortSelect.value = state.sort;
            persist();
        }
        draw();
    }

    heroSelect.addEventListener('change', () => {
        state.heroId = heroSelect.value;
        persist();
        draw();
    });

    sortSelect.addEventListener('change', () => {
        state.sort = sortSelect.value as SortMode;
        persist();
        void ensureAspectsThenDraw();
    });

    groupToggle.addEventListener('click', () => {
        state.groupByHero = !state.groupByHero;
        setPressed(groupToggle, state.groupByHero);
        persist();
        draw();
    });

    preconToggle.addEventListener('click', () => {
        state.hidePrecons = !state.hidePrecons;
        setPressed(preconToggle, state.hidePrecons);
        persist();
        draw();
    });

    return {
        render(choices: T[]): void {
            source = choices;
            refreshHeroOptions();
            void ensureAspectsThenDraw();
        },
    };
}
