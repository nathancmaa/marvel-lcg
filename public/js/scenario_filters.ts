// Filtering, sorting and grouping for the Quick Game scenario picker.
//
// A companion to deck_filters.ts, and deliberately the same shape: the two
// controls bars sit on one page and should behave the same way. It reuses that
// module's styles rather than defining its own.
//
// Only the box a scenario shipped in is offered as a dimension. sets_info.json
// records `name`, `scenarios`, `heroes`, `encounters`, `out_of_print`, `max_id`
// and `underlings` -- there is no release date, wave or phase anywhere in it, so
// filtering by year would mean hardcoding a product-to-year table that goes
// stale with every new pack. The numeric prefix on each set key ("1. Core Set",
// "60. Fear No Evil") is a real release ordering, and is used for that instead.

export type ScenarioFilterChoice = {
    id: string;
    name: string;
    productLabel: string;
    productOrder: number;
    /** Where it sits inside its own box, in the order the box presents them. */
    boxIndex: number;
};

type SortMode = 'default' | 'release' | 'name';

type ControlState = {
    product: string;
    sort: SortMode;
    groupByProduct: boolean;
};

const STORAGE_KEY = 'marvel_lcg_solo_scenario_filters';

const SORT_LABELS: ReadonlyArray<readonly [SortMode, string]> = [
    ['default', 'New content first'],
    ['release', 'Release order'],
    ['name', 'Name'],
];

const DEFAULT_STATE: ControlState = {
    product: '',
    sort: 'default',
    groupByProduct: false,
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
            product: typeof parsed.product === 'string' ? parsed.product : '',
            sort,
            groupByProduct: parsed.groupByProduct === true,
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

function compareText(left: string, right: string): number {
    return left.localeCompare(right, undefined, {sensitivity: 'base', numeric: true});
}

export type ScenarioFiltersOptions<T extends ScenarioFilterChoice> = {
    /** The `.choice-grid` the scenario buttons are rendered into. */
    listHost: HTMLElement;
    /** Builds the button for one scenario; owned by the caller. */
    createButton: (choice: T) => HTMLElement;
    /** Marks newly added content, which the default ordering floats to the top. */
    isNew: (choice: T) => boolean;
    /** Called after every re-render so the caller can restore selection state. */
    onRendered?: () => void;
};

export type ScenarioFilters<T extends ScenarioFilterChoice> = {
    render(choices: T[]): void;
    /**
     * Redraw with the current list and options.
     *
     * For state the bar reads but does not own: each tile is marked with how
     * far the selected hero has got against that villain, and choosing a
     * different hero changes every one of those marks.
     */
    refresh(): void;
    /**
     * Clear the box filter so every scenario is listed again.
     *
     * For arriving with a scenario already chosen: the filter is remembered
     * between visits, so a scenario picked from the coverage grid could land
     * on a list that was narrowed to some other box and never show the tile
     * that is actually selected.
     */
    showAllProducts(): void;
    /**
     * Narrow the list to one box, as if the dropdown were used.
     *
     * The counterpart of deck_filters' filterToHero, and there for the same
     * reason: something else picked a scenario, and the list should be showing
     * the tile that got picked rather than whatever it was last narrowed to.
     */
    filterToBox(productLabel: string): void;
};

export function createScenarioFilters<T extends ScenarioFilterChoice>(
    options: ScenarioFiltersOptions<T>,
): ScenarioFilters<T> {
    const {listHost, createButton, isNew, onRendered} = options;
    const state = readState();
    let source: T[] = [];
    let products: string[] = [];

    const bar = document.createElement('div');
    bar.className = 'deck-filters';
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', 'Scenario list options');

    const productSelect = document.createElement('select');
    productSelect.className = 'deck-filter-select';
    productSelect.id = 'scenario-filter-product';

    const productField = document.createElement('label');
    productField.className = 'deck-filter-field';
    productField.htmlFor = productSelect.id;
    productField.append(labelText('Box'), productSelect);

    const sortSelect = document.createElement('select');
    sortSelect.className = 'deck-filter-select';
    sortSelect.id = 'scenario-filter-sort';
    for (const [mode, label] of SORT_LABELS) {
        const option = document.createElement('option');
        option.value = mode;
        option.textContent = label;
        sortSelect.appendChild(option);
    }
    sortSelect.value = state.sort;

    const sortField = document.createElement('label');
    sortField.className = 'deck-filter-field';
    sortField.htmlFor = sortSelect.id;
    sortField.append(labelText('Sort by'), sortSelect);

    const groupToggle = createToggle('Group by box', state.groupByProduct);

    const count = document.createElement('span');
    count.className = 'deck-filter-count';
    count.setAttribute('aria-live', 'polite');

    bar.append(productField, sortField, groupToggle, count);
    listHost.parentElement?.insertBefore(bar, listHost);

    // Working through the boxes in order is a real way to play this game, and
    // doing it from the dropdown means opening it and finding the next line
    // every time. The stepper only appears while a box is actually selected:
    // with "All boxes" showing there is no sequence to be at a point in.
    const stepper = document.createElement('div');
    stepper.className = 'filter-stepper';
    stepper.hidden = true;

    const previousBox = document.createElement('button');
    previousBox.type = 'button';
    previousBox.className = 'deck-filter-toggle';
    previousBox.textContent = '‹ Previous box';

    const stepperCount = document.createElement('span');
    stepperCount.className = 'filter-stepper-count';
    stepperCount.setAttribute('aria-live', 'polite');

    const nextBox = document.createElement('button');
    nextBox.type = 'button';
    nextBox.className = 'deck-filter-toggle';
    nextBox.textContent = 'Next box ›';

    stepper.append(previousBox, stepperCount, nextBox);
    listHost.parentElement?.insertBefore(stepper, listHost.nextSibling);

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

    function persist(): void {
        writeState(state);
    }

    function refreshProductOptions(): void {
        // Ordered by release rather than alphabetically: the boxes came out in
        // a sequence, and the list reads better in it.
        const seen = new Map<string, number>();
        for (const choice of source) {
            if (!seen.has(choice.productLabel)) {
                seen.set(choice.productLabel, choice.productOrder);
            }
        }
        const products_ = [...seen.entries()]
            .sort((left, right) => left[1] - right[1] || compareText(left[0], right[0]))
            .map(([label]) => label);

        productSelect.replaceChildren();
        const all = document.createElement('option');
        all.value = '';
        all.textContent = 'All boxes';
        productSelect.appendChild(all);
        for (const product of products_) {
            const option = document.createElement('option');
            option.value = product;
            option.textContent = product;
            productSelect.appendChild(option);
        }

        // A remembered box with nothing installed falls back to "All" rather
        // than leaving the picker mysteriously empty.
        if (state.product && !products_.includes(state.product)) {
            state.product = '';
            persist();
        }
        productSelect.value = state.product;
        products = products_;
    }

    function applySort(choices: T[]): T[] {
        const sorted = [...choices];
        sorted.sort((left, right) => {
            if (state.sort === 'default') {
                // The picker has always floated new content to the top; that
                // stays the default so the page opens as it used to.
                const newness = Number(isNew(right)) - Number(isNew(left));
                if (newness !== 0) {
                    return newness;
                }
            } else if (state.sort === 'release') {
                if (left.productOrder !== right.productOrder) {
                    return left.productOrder - right.productOrder;
                }
            }
            // Only "By name" is alphabetical. The other two are about release
            // order, and a box has one of its own -- the Core Set opens with
            // Rhino and ends with Ultron, which alphabetical turned into Klaw,
            // Rhino, Ultron and made the first scenario look like the third.
            if (state.sort !== 'name' && left.productLabel === right.productLabel
                && left.boxIndex !== right.boxIndex) {
                return left.boxIndex - right.boxIndex;
            }
            return compareText(left.name, right.name) || compareText(left.id, right.id);
        });
        return sorted;
    }

    type Section = {label: string | null; items: T[]};

    function arrange(): Section[] {
        const filtered = source.filter(
            (choice) => !state.product || choice.productLabel === state.product);

        if (!state.groupByProduct) {
            return [{label: null, items: applySort(filtered)}];
        }

        const groups = new Map<string, {order: number; items: T[]}>();
        for (const choice of filtered) {
            const group = groups.get(choice.productLabel);
            if (group) {
                group.items.push(choice);
            } else {
                groups.set(choice.productLabel, {
                    order: choice.productOrder,
                    items: [choice],
                });
            }
        }
        return [...groups.entries()]
            .sort((left, right) =>
                left[1].order - right[1].order || compareText(left[0], right[0]))
            .map(([label, group]) => ({label, items: applySort(group.items)}));
    }

    function draw(): void {
        const sections = arrange();
        const total = sections.reduce((sum, section) => sum + section.items.length, 0);

        listHost.replaceChildren();
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

        if (total === 0 && source.length > 0) {
            const empty = document.createElement('p');
            empty.className = 'deck-filter-empty';
            empty.textContent = 'No scenarios match these options.';
            listHost.appendChild(empty);
        }

        count.textContent = total === source.length
            ? `${total} scenario${total === 1 ? '' : 's'}`
            : `${total} of ${source.length} scenarios`;

        updateStepper();
        onRendered?.();
    }

    function updateStepper(): void {
        const index = products.indexOf(state.product);
        stepper.hidden = !state.product || index < 0;
        if (stepper.hidden) {
            return;
        }
        stepperCount.textContent = `Box ${index + 1} of ${products.length}`;
        previousBox.disabled = index === 0;
        nextBox.disabled = index === products.length - 1;
    }

    /** Move to the box `offset` along, staying inside the list. */
    function stepBox(offset: number): void {
        const index = products.indexOf(state.product);
        const next = products[index + offset];
        if (index < 0 || next === undefined) {
            return;
        }
        state.product = next;
        productSelect.value = next;
        persist();
        draw();
    }

    previousBox.addEventListener('click', () => stepBox(-1));
    nextBox.addEventListener('click', () => stepBox(1));

    productSelect.addEventListener('change', () => {
        state.product = productSelect.value;
        persist();
        draw();
    });

    sortSelect.addEventListener('change', () => {
        state.sort = sortSelect.value as SortMode;
        persist();
        draw();
    });

    groupToggle.addEventListener('click', () => {
        state.groupByProduct = !state.groupByProduct;
        groupToggle.setAttribute('aria-pressed', String(state.groupByProduct));
        groupToggle.classList.toggle('active', state.groupByProduct);
        persist();
        draw();
    });

    return {
        render(choices: T[]): void {
            source = choices;
            refreshProductOptions();
            draw();
        },
        refresh(): void {
            draw();
        },
        showAllProducts(): void {
            if (!state.product) {
                return;
            }
            state.product = '';
            productSelect.value = '';
            writeState(state);
            draw();
        },
        filterToBox(productLabel: string): void {
            // Only if the box is actually offered: a scenario whose product is
            // missing from sets_info would otherwise select a value the box
            // does not have and silently empty the list.
            const offered = Array.prototype.some.call(
                productSelect.options,
                (option: HTMLOptionElement) => option.value === productLabel);
            if (!offered) {
                return;
            }
            state.product = productLabel;
            productSelect.value = productLabel;
            writeState(state);
            draw();
        },
    };
}
