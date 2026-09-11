type SetInfo = {
    name?: string;
    scenarios: string[];
    heroes?: string[];
};

type ScenarioData = {
    name: string;
    villain: string[];
    expert: boolean;
    schemes: string[];
    set_aside: string[];
    encounters: string[];
    underling_sets?: string[];
    encounter_sets: string[];
    modular_sets: string[];
};

/** Only the part of /get_matchup_matrix a villain tile needs. */
type MatchupMatrix = {
    available: boolean;
    cells?: Record<string, {best_beaten?: number}>;
};

type UnderlingData = {
    name: string;
    villain: string[];
    expert_villain: string[];
    set_aside: string[];
    encounters: string[];
};

type UnderlingChoice = {
    id: string;
    name: string;
    imageId: string;
    data: UnderlingData;
};

type HeroData = {
    name: string;
    deck_name?: string;
    hero: string[];
    player_deck: string[];
    metadata?: Record<string, string>;
};

type ScenarioChoice = {
    id: string;
    name: string;
    imageId: string;
    data: ScenarioData;
    expertId: string | null;
    productLabel: string;
    // Position of the box in the release sequence, from the numeric prefix on
    // its sets_info key. Lets the picker order boxes as they came out.
    productOrder: number;
    // Where the scenario sits inside its own box, which sets_info lists in
    // the order the box presents them: Rhino, Klaw, Ultron in the Core Set,
    // not the alphabetical Klaw, Rhino, Ultron.
    boxIndex: number;
};

type HeroChoice = {
    id: string;
    name: string;
    imageId: string;
    data: HeroData;
    isUserDeck: boolean;
    isResolvedMarvelCdb?: boolean;
};

type SoloGamePayload = {
    campaign_json: string;
    encounter_set_names: string[];
    hero_json: string[];
    seed: number;
    timeout: number;
    challenges: string[];
    rules: string[];
    campaign_log: Record<string, string>;
};

import {
    DeckSource,
    DeckSourceController,
    MarvelCdbDeckData,
    createDeckSourceController,
    marvelCdbDeckUrl,
} from './marvelcdb_deck.js';
import { withCardImageRevision } from './card_image_url.js';
import { DeckFilters, buildHeroLabels, createDeckFilters, heroKeyOf } from './deck_filters.js';
import { isFavorite, loadFavorites, onFavoritesChanged, toggleFavorite } from './favorites.js';
import { UserSettings } from './user_settings.js';
import { beatenClass, beatenLabel } from './beaten.js';
import { AspectDeckPicker, createAspectDeckPicker } from './aspect_decks.js';
import { UniversalDeckPicker, createUniversalDeckPicker } from './universal_decks.js';
import { ScenarioFilters, createScenarioFilters } from './scenario_filters.js';

const scenarioStorageKey = 'marvel_lcg_solo_scenario';
const heroStorageKey = 'marvel_lcg_solo_hero';
const underlingStorageKey = 'marvel_lcg_solo_underling';
const standardSetStorageKey = 'marvel_lcg_solo_standard_set';
const heroicLevelStorageKey = 'marvel_lcg_solo_heroic_level'
const aspectHeroStorageKey = 'marvel_lcg_solo_aspect_hero';

/**
 * A hero and scenario named in the URL, from the coverage grid.
 *
 * Read once at load. These win over the remembered choices for this visit
 * only and are not written back, so arriving from a square does not quietly
 * rewrite what the picker opens on next time.
 */
const requestedGame = (() => {
    const query = new URLSearchParams(window.location.search);
    return {
        hero: query.get('hero') ?? '',
        scenario: query.get('scenario') ?? '',
    };
})();
const newScenarioIds = new Set(['kingpin', 'protection_racket', 'the_raft_breakout', 'art_museum_heist', 'the_getaway', 'stop_the_presses']);
const newUnderlingIds = new Set(['bullseye', 'electro', 'hammerhead', 'purple_man', 'typhoid_mary']);
const newHeroIds = new Set(['echo', 'daredevil', 'jessica_jones']);

const scenarioList = document.querySelector<HTMLElement>('#scenario-list')!;
const heroList = document.querySelector<HTMLElement>('#hero-list')!;
const scenarioStatus = document.querySelector<HTMLElement>('#scenario-status')!;
const heroStatus = document.querySelector<HTMLElement>('#hero-status')!;
const scenarioSelection = document.querySelector<HTMLElement>('#scenario-selection')!;
const heroSelection = document.querySelector<HTMLElement>('#hero-selection')!;
const playButton = document.querySelector<HTMLButtonElement>('#play-button')!;
const summaryHeroImage = document.querySelector<HTMLImageElement>('#summary-hero-image')!;
const summaryHero = document.querySelector<HTMLElement>('#summary-hero')!;
const summaryDeck = document.querySelector<HTMLElement>('#summary-deck')!;
const summaryScenario = document.querySelector<HTMLElement>('#summary-scenario')!;
const summaryDifficulty = document.querySelector<HTMLElement>('#summary-difficulty')!;
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;
const expertMode = document.querySelector<HTMLInputElement>('#expert-mode')!;
const expertModeDescription = document.querySelector<HTMLElement>('#expert-mode-description')!;
const difficultySelection = document.querySelector<HTMLElement>('#difficulty-selection')!;
const difficultyStepNumber = document.querySelector<HTMLElement>('#difficulty-step-number')!;
const standardSet = document.querySelector<HTMLSelectElement>('#standard-set')!;
const heroicLevel = document.querySelector<HTMLSelectElement>('#heroic-level')!;
const standardSetDescription = document.querySelector<HTMLElement>('#standard-set-description')!;
const randomizeStandardSet = document.querySelector<HTMLButtonElement>('#randomize-standard-set')!;
const heroSection = document.querySelector<HTMLElement>('#hero-section')!;
const aspectHero = document.querySelector<HTMLSelectElement>('#aspect-hero')!;
const underlingSection = document.querySelector<HTMLElement>('#underling-section')!;
const underlingList = document.querySelector<HTMLElement>('#underling-list')!;
const underlingSelection = document.querySelector<HTMLElement>('#underling-selection')!;
let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let selectedUnderling: UnderlingChoice | null = null;
let underlingChoices: UnderlingChoice[] = [];
let isStarting = false;
let heroChoices: HeroChoice[] = [];
let scenarioChoices: ScenarioChoice[] = [];
let heroBeforeMarvelCdb: HeroChoice | null = null;

const deckFilters: DeckFilters<HeroChoice> = createDeckFilters<HeroChoice>({
    listHost: heroList,
    createButton: (choice) => {
        const button = createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectHero(choice),
            !choice.isUserDeck && newHeroIds.has(choice.id),
        );
        button.classList.toggle('user-deck', choice.isUserDeck);
        return withFavoriteStar(button, choice.id, choice.name);
    },
    // Re-drawing the list discards the selected styling, so put it back.
    onRendered: () => markSelected(heroList, selectedHero?.id ?? ''),
});

const scenarioFilters: ScenarioFilters<ScenarioChoice> =
    createScenarioFilters<ScenarioChoice>({
        listHost: scenarioList,
        createButton: (choice) => {
            const button = createChoiceButton(
                choice.id,
                choice.name,
                choice.imageId,
                () => selectScenario(choice),
                newScenarioIds.has(choice.id),
            );
            const product = document.createElement('span');
            product.className = 'scenario-product-label';
            product.textContent = choice.productLabel;
            button.appendChild(product);
            markBeaten(button, choice);
            return button;
        },
        isNew: (choice) => newScenarioIds.has(choice.id),
        onRendered: () => markSelected(scenarioList, selectedScenario?.id ?? ''),
    });

// The precon is the deck that ships with the hero; a MarvelCDB deck replaces
// only the player deck, so the hero choice stays the source of truth for the
// signature cards, obligations and nemesis set.
/**
 * One hero's worth of choice, for two-handed games.
 *
 * The picker below the tabs never changes: one tile selected at a time, one
 * deck source, one panel. The tabs say which of these two the selection is
 * being made for, and switching them puts the other one back.
 *
 * `deck` is what Play would send -- the hero's own data with whatever deck has
 * replaced its player cards -- captured on the way out of a slot so the
 * MarvelCDB deck or aspect deck chosen for a hero is still theirs when you
 * come back.
 */
type PlayerSlot = {
    hero: HeroChoice | null;
    deck: HeroData | null;
    source: DeckSource;
    marvelCdbDeck: MarvelCdbDeckData | null;
    /**
     * What the summary calls this slot's deck.
     *
     * Kept as text rather than worked out again later: composeHeroDeck keeps
     * an aspect or universal deck's cards and not its name, so the slot has
     * no way back to "Team Tactics (aspect deck)" once the pickers have moved
     * on to the other player.
     */
    deckLabel: string;
};

const handModeButtons = [
    document.querySelector<HTMLButtonElement>('#hand-mode-1')!,
    document.querySelector<HTMLButtonElement>('#hand-mode-2')!,
];
const playerTabs = document.querySelector<HTMLElement>('#hero-player-tabs')!;
const playerTabButtons = [
    document.querySelector<HTMLButtonElement>('#player-tab-0')!,
    document.querySelector<HTMLButtonElement>('#player-tab-1')!,
];

function emptySlot(): PlayerSlot {
    return {hero: null, deck: null, source: 'precon', marvelCdbDeck: null, deckLabel: ''};
}

let twoHanded = false;
let activePlayer = 0;
const playerSlots: PlayerSlot[] = [emptySlot(), emptySlot()];

let deckSourceController: DeckSourceController | null = null;
let aspectDeckPicker: AspectDeckPicker | null = null;
let universalDeckPicker: UniversalDeckPicker | null = null;

/** The universal deck for whoever is selected, when that is the deck source. */
function currentUniversalDeck() {
    if (deckSourceController?.getSource() !== 'universal' || !selectedHero) {
        return null;
    }
    return universalDeckPicker?.getDeckFor(selectedHero.id) ?? null;
}

/** Keep the universal panel talking about the hero that is actually selected. */
function refreshUniversalPanel(): void {
    if (deckSourceController?.getSource() !== 'universal') {
        return;
    }
    universalDeckPicker?.show(selectedHero?.id ?? '', selectedHero?.name ?? '');
}

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function getFirstCardId(cardIds: string[]): string {
    return cardIds[0]?.split(',')[0] ?? '';
}

function getProductLabel(label: string, info: SetInfo): string {
    const match = label.match(/^(\d+)\.\s*(.+)$/);
    const order = match ? Number(match[1]) : 0;
    const productName = match?.[2] ?? label;
    const hasHeroes = (info.heroes?.length ?? 0) > 0;
    const hasScenarios = (info.scenarios?.length ?? 0) > 0;

    if (order === 1 || info.name === 'core') {
        return productName;
    }
    if (hasHeroes && hasScenarios) {
        return `${productName} · Expansion`;
    }
    if (hasScenarios) {
        return `${productName} · Scenario Pack`;
    }
    return productName;
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

/**
 * What you are about to play, beside the button that starts it.
 *
 * The three choices sit in three sections up the page, so confirming them
 * meant scrolling back through the deck grid -- and after a browser back, a
 * refresh, or arriving from the coverage grid, what is selected is restored
 * rather than chosen, which is exactly when it is worth checking. This says
 * it in one place, at the point of no return.
 */
/**
 * The deck the pickers are currently pointing at, named as the summary names
 * it -- which is not always the tile that looks selected, since an aspect deck
 * or a loaded netdeck replaces it.
 */
function currentDeckLabel(hero: HeroChoice): string {
    const source = deckSourceController?.getSource();
    const aspectDeck = source === 'aspect' ? aspectDeckPicker?.getDeck() ?? null : null;
    const universalDeck = currentUniversalDeck();
    const resolved = source === 'marvelcdb' ? deckSourceController?.getDeck() ?? null : null;
    return aspectDeck
        ? `${aspectDeck.name} (aspect deck)`
        : universalDeck
            ? `${universalDeck.name} (${universalDeck.aspect})`
            : source === 'universal'
                ? 'No universal deck for this hero'
                : resolved
                    ? String(resolved.deck_name ?? resolved.name ?? 'MarvelCDB deck')
                    : hero.isUserDeck
                        ? hero.name
                        : `${hero.name} (precon)`;
}

function updateMatchupSummary(): void {
    const hero = selectedHero;

    if (twoHanded) {
        const names = playerSlots.map((slot, player) => {
            const who = player === activePlayer ? hero : slot.hero;
            return who ? who.data.name : 'not chosen';
        });
        summaryHero.textContent = `P1 ${names[0]} · P2 ${names[1]}`;
    } else {
        summaryHero.textContent = hero ? hero.data.name : 'Not selected';
    }
    if (hero) {
        summaryHeroImage.src = withCardImageRevision(`/${hero.imageId}`);
        summaryHeroImage.alt = hero.data.name;
    }
    summaryHeroImage.hidden = !hero;

    // Which deck is actually going to the table. Two-handed names both, the
    // way the hero line does: the deck for the player whose tab is not open is
    // just as much part of the game about to start, and reading only the
    // active one made the summary look like a one-hero game.
    if (twoHanded) {
        const decks = playerSlots.map((slot, player) => {
            if (player === activePlayer) {
                return hero ? currentDeckLabel(hero) : 'not chosen';
            }
            return slot.hero ? (slot.deckLabel || slot.hero.name) : 'not chosen';
        });
        summaryDeck.textContent = `P1 ${decks[0]} · P2 ${decks[1]}`;
    } else {
        summaryDeck.textContent = hero ? currentDeckLabel(hero) : '—';
    }

    summaryScenario.textContent = selectedScenario
        ? selectedScenario.name + (selectedUnderling ? ` · ${selectedUnderling.name}` : '')
        : 'Not selected';
    summaryDifficulty.textContent = difficultySelection.textContent || 'Standard';
}

function updatePlayButton(): void {
    updateMatchupSummary();
    const source = deckSourceController?.getSource();
    const awaitingDeck = (source === 'marvelcdb' && !deckSourceController?.getDeck())
        || (source === 'aspect' && !aspectDeckPicker?.getDeck())
        || (source === 'universal' && !currentUniversalDeck());
    // In two-handed the other slot has to be filled as well, and the one on
    // screen is not in its slot until the tabs are switched.
    const otherPlayerReady = !twoHanded
        || playerSlots.every((slot, player) => player === activePlayer || slot.hero);
    playButton.disabled = isStarting
        || deckSourceController?.isBusy() === true
        || !selectedScenario
        || !selectedHero
        || !otherPlayerReady
        || ((selectedScenario.data.underling_sets?.length ?? 0) > 0 && !selectedUnderling)
        || awaitingDeck;
}

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const isSelected = button.dataset.id === selectedId;
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected.toString());
    });
}

function selectUnderling(choice: UnderlingChoice): void {
    selectedUnderling = choice;
    localStorage.setItem(underlingStorageKey, choice.id);
    underlingSelection.textContent = choice.name;
    markSelected(underlingList, choice.id);
    errorMessage.textContent = '';
    updatePlayButton();
}

async function loadUnderlings(ids: string[]): Promise<void> {
    const generation = ids.join('|');
    selectedUnderling = null;
    underlingChoices = [];
    underlingList.replaceChildren();
    underlingSelection.textContent = 'Not selected';
    underlingSection.hidden = ids.length === 0;
    difficultyStepNumber.textContent = ids.length ? '4' : '3';
    if (!ids.length) {
        updatePlayButton();
        return;
    }

    const choices = (await Promise.all(ids.map(async (id): Promise<UnderlingChoice | null> => {
        try {
            const data = await fetchJson<UnderlingData>(
                `/get_encounter_set_json?${encodeURIComponent(id)}`,
            );
            const imageId = getFirstCardId(data.villain ?? []);
            if (!data.name || !imageId) {
                return null;
            }
            return {id, name: data.name, imageId, data};
        } catch (error) {
            console.warn(`Failed to load underling ${id}`, error);
            return null;
        }
    }))).filter((choice): choice is UnderlingChoice => choice !== null);

    if (selectedScenario?.data.underling_sets?.join('|') !== generation) {
        return;
    }
    underlingChoices = choices;
    for (const choice of choices) {
        underlingList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectUnderling(choice),
            newUnderlingIds.has(choice.id),
        ));
    }
    const savedId = localStorage.getItem(underlingStorageKey);
    const savedChoice = choices.find((choice) => choice.id === savedId) ?? choices[0];
    if (savedChoice) {
        selectUnderling(savedChoice);
    }
    updatePlayButton();
}

/**
 * Whether an encounter set is one of the Standard difficulty sets.
 *
 * Matches the engine's own family rule, which is what lets a chosen set stand
 * in for the one a scenario names: see SceneLoader.GetEncounterSetFamily.
 */
function isStandardSet(name: string): boolean {
    return name === 'standard' || name.startsWith('standard_');
}

/**
 * Restate the difficulty from the two controls that make it up.
 *
 * Outside Expert mode the Standard set is the whole of the difficulty, so it
 * is named on its own rather than as "Standard · Standard II".
 */
function updateDifficulty(): void {
    const dealt = selectedScenario
        ? (selectedScenario.data.encounter_sets ?? []).some(isStandardSet)
        : true;
    standardSet.disabled = !dealt;
    // Nothing to roll for when the scenario is dealt no Standard set at all.
    randomizeStandardSet.disabled = !dealt;
    standardSetDescription.textContent = dealt
        ? 'Standard II and III stand in for Standard I rather than stacking on it.'
        : 'This scenario is played without a Standard encounter set.';

    const setName = dealt
        ? standardSet.selectedOptions[0]?.text ?? 'Standard'
        : 'Standard';
    // Heroic sits alongside the rest rather than replacing it: it stacks with
    // Expert and with whichever Standard set is dealt.
    const level = Number(heroicLevel.value);
    const heroic = Number.isInteger(level) && level > 0 ? ` · Heroic ${level}` : '';
    const base = expertMode.checked
        ? (dealt ? `Expert · ${setName}` : 'Expert')
        : setName;
    difficultySelection.textContent = `${base}${heroic}`;
    // The summary reads this line, and difficulty changes do not otherwise
    // touch the play button, so it would go stale without this.
    updateMatchupSummary();
}

function selectScenario(choice: ScenarioChoice): void {
    selectedScenario = choice;
    localStorage.setItem(scenarioStorageKey, choice.id);
    scenarioSelection.textContent = choice.name;
    markSelected(scenarioList, choice.id);
    errorMessage.textContent = '';

    const hasExpertMode = choice.expertId !== null;
    expertMode.disabled = !hasExpertMode;
    if (!hasExpertMode) {
        expertMode.checked = false;
    }
    expertModeDescription.textContent = hasExpertMode
        ? 'Villain stages II–III with the Expert encounter set.'
        : 'Expert setup is not available for this scenario.';
    updateDifficulty();
    void loadUnderlings(choice.data.underling_sets ?? []);
    updatePlayButton();
}

/** Write the summary, making the deck's name a link when it has a page. */
function renderHeroSelection(prefix: string, name: string, href: string): void {
    if (!href) {
        heroSelection.textContent = prefix + name;
        return;
    }
    const link = document.createElement('a');
    link.className = 'deck-link';
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = name;
    heroSelection.replaceChildren(prefix, link);
}

/**
 * Name the deck that is actually going to be played.
 *
 * In aspect mode the tile is not the deck: its player deck is discarded and
 * the aspect list used instead, so naming the tile was the one thing this
 * summary could say that was not true.
 *
 * Every deck that came from MarvelCDB records where -- a synced deck as much
 * as one just pasted in -- so the title is the way back to its page.
 */
function updateHeroSelection(): void {
    const hero = selectedHero;
    if (!hero) {
        heroSelection.textContent = 'Not selected';
        return;
    }
    if (deckSourceController?.getSource() !== 'aspect') {
        renderHeroSelection('', hero.name, marvelCdbDeckUrl(hero.data));
        return;
    }
    const label = aspectHero.selectedOptions[0]?.text ?? hero.name;
    const deck = aspectDeckPicker?.getDeck();
    if (!deck) {
        renderHeroSelection('', label, '');
        return;
    }
    renderHeroSelection(`${label} · `, deck.name, deck.url);
}

/** The precon deck belonging to whichever hero a choice represents. */
function preconFor(choice: HeroChoice | null): string {
    if (!choice) {
        return '';
    }
    const key = heroKeyOf(choice);
    return heroChoices.find(
        (other) => !other.isUserDeck && heroKeyOf(other) === key)?.id ?? '';
}

/**
 * Fill the aspect panel's hero dropdown.
 *
 * Precons only. An aspect deck replaces the player deck outright, so all that
 * is taken from the hero is its identity, signature cards, obligation and
 * nemesis set -- which every precon carries and a netdeck only repeats, so
 * offering both would be two spellings of one choice.
 */
function populateAspectHeroes(): void {
    const precons = heroChoices.filter((choice) => !choice.isUserDeck);
    const labels = buildHeroLabels(precons);
    const options = precons
        .map((choice) => ({
            id: choice.id,
            label: labels.get(heroKeyOf(choice)) ?? choice.name,
        }))
        .sort((left, right) => left.label.localeCompare(
            right.label, undefined, {sensitivity: 'base'}));

    aspectHero.replaceChildren(
        ...options.map((option) => new Option(option.label, option.id)));
    aspectHero.disabled = options.length === 0;

    const saved = localStorage.getItem(aspectHeroStorageKey) ?? '';
    aspectHero.value = options.some((option) => option.id === saved)
        ? saved
        // Falling back to the hero already picked from the grid keeps the
        // switch into aspect mode from silently changing who is playing.
        : (preconFor(selectedHero) || options[0]?.id) ?? '';
}

/** Make the aspect panel's dropdown the selected hero. */
function applyAspectHero(): void {
    const choice = heroChoices.find((item) => item.id === aspectHero.value);
    if (choice) {
        selectHero(choice);
    }
}

function selectHero(choice: HeroChoice, keepMarvelCdbDeck = false): void {
    if (!keepMarvelCdbDeck) {
        removeResolvedMarvelCdbChoice();
        heroBeforeMarvelCdb = null;
    }
    selectedHero = choice;
    if (!choice.isResolvedMarvelCdb) {
        localStorage.setItem(heroStorageKey, choice.id);
    }
    updateHeroSelection();
    refreshUniversalPanel();
    // Every villain tile is marked against the hero, so they all change.
    scenarioFilters.refresh();
    paintPlayerTabs();
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    // Picking a different hero by hand abandons a loaded deck; a deck that
    // switched the hero itself keeps it, having just supplied it.
    if (!keepMarvelCdbDeck) {
        deckSourceController?.clear();
    }
    updatePlayButton();
}

function removeResolvedMarvelCdbChoice(): void {
    heroChoices = heroChoices.filter((choice) => !choice.isResolvedMarvelCdb);
    heroList.querySelector('.resolved-marvelcdb-deck')?.remove();
}

function selectResolvedMarvelCdbDeck(deck: HeroData): string {
    if (selectedHero && !selectedHero.isResolvedMarvelCdb) {
        heroBeforeMarvelCdb = selectedHero;
    }
    removeResolvedMarvelCdbChoice();

    const metadata = deck.metadata ?? {};
    const marvelCdbId = metadata.marvelcdb_id ?? 'loaded';
    const marvelCdbKind = metadata.marvelcdb_kind ?? 'deck';
    const choice: HeroChoice = {
        id: `marvelcdb-${marvelCdbKind}-${marvelCdbId}`,
        name: deck.deck_name ?? deck.name,
        imageId: getFirstCardId(deck.hero ?? []),
        data: deck,
        isUserDeck: true,
        isResolvedMarvelCdb: true,
    };
    heroChoices.unshift(choice);

    const button = createChoiceButton(
        choice.id,
        choice.name,
        choice.imageId,
        () => selectHero(choice, true),
    );
    button.classList.add('user-deck', 'resolved-marvelcdb-deck');
    heroList.prepend(button);
    selectHero(choice, true);
    button.scrollIntoView({block: 'nearest', behavior: 'smooth'});
    return `Loaded and selected ${choice.name}.`;
}

function leaveMarvelCdbMode(): void {
    if (!selectedHero?.isResolvedMarvelCdb) {
        removeResolvedMarvelCdbChoice();
        heroBeforeMarvelCdb = null;
        return;
    }

    const previous = heroBeforeMarvelCdb;
    removeResolvedMarvelCdbChoice();
    heroBeforeMarvelCdb = null;
    if (previous) {
        selectHero(previous, true);
    } else {
        selectedHero = null;
        heroSelection.textContent = 'Not selected';
        markSelected(heroList, '');
        updatePlayButton();
    }
}

function createChoiceButton(
    id: string,
    name: string,
    imageId: string,
    onSelect: () => void,
    isNew = false,
): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice-card';
    button.dataset.id = id;
    button.setAttribute('aria-pressed', 'false');
    button.classList.toggle('new-content', isNew);

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${imageId}`);
    image.alt = '';

    const title = document.createElement('span');
    title.className = 'choice-name';
    title.textContent = name;

    button.append(image, title);
    button.addEventListener('click', onSelect);
    return button;
}

/**
 * How far each pairing has been beaten, keyed `<hero code>|<scenario id>`.
 *
 * The whole grid rather than a column summary, because the question a villain
 * tile answers is about the hero standing next to it: "have I beaten this one
 * with them". Taking the best clear by anybody marked a villain as done while
 * the hero on screen had never faced them, which is the opposite of what the
 * mark is for.
 */
let beatenCells = new Map<string, number>();

async function loadBeatenScenarios(): Promise<Map<string, number>> {
    const cells = new Map<string, number>();
    try {
        const matrix = await fetchJson<MatchupMatrix>('/get_matchup_matrix?');
        if (!matrix.available || !matrix.cells) {
            return cells;
        }
        for (const [key, cell] of Object.entries(matrix.cells)) {
            cells.set(key, cell.best_beaten ?? 0);
        }
    } catch (error) {
        // History is optional, and a picker that cannot reach it still picks.
        console.warn('Could not load which villains have been beaten', error);
    }
    return cells;
}

/** The identity card the game history keys a hero on, e.g. `40001a`. */
function heroCodeOf(choice: HeroChoice): string {
    return String(choice.data.hero?.[0] ?? '').split(',')[0].trim().toLowerCase();
}

function beatenBySelectedHero(scenarioId: string): number {
    if (!selectedHero) {
        return 0;
    }
    const code = heroCodeOf(selectedHero);
    return code ? beatenCells.get(`${code}|${scenarioId}`) ?? 0 : 0;
}

function markBeaten(button: HTMLButtonElement, choice: ScenarioChoice): void {
    const beaten = beatenBySelectedHero(choice.id);
    const stripeClass = beatenClass(beaten);
    const who = selectedHero ? selectedHero.data.name : 'this hero';
    button.title = `${choice.name} — ${who}: ${beatenLabel(beaten)}`;
    if (!stripeClass) {
        return;
    }
    const stripe = document.createElement('span');
    stripe.className = `beaten-stripe ${stripeClass}`;
    button.appendChild(stripe);
}

/**
 * Pair a deck tile with its own star, in a slot the two share.
 *
 * The star has to be a button of its own -- it is a second action on the tile,
 * and a control nested inside a button is neither valid nor reachable from the
 * keyboard. So the tile keeps its markup exactly and gains a sibling, with the
 * slot around them taking over the tile's width so the grid still lays out one
 * card per cell at every breakpoint.
 */
function withFavoriteStar(tile: HTMLButtonElement, id: string, name: string): HTMLElement {
    const slot = document.createElement('div');
    slot.className = 'choice-slot';

    const star = document.createElement('button');
    star.type = 'button';
    star.className = 'favorite-star';
    star.textContent = '★';

    function paint(): void {
        const starred = isFavorite(id);
        star.classList.toggle('active', starred);
        star.setAttribute('aria-pressed', String(starred));
        star.title = starred ? `Remove ${name} from favorites` : `Add ${name} to favorites`;
        star.setAttribute('aria-label', star.title);
    }
    paint();

    star.addEventListener('click', () => {
        toggleFavorite(id);
        paint();
        // Starring while "Favorites only" is on removes the tile under the
        // pointer, which is the honest thing for the filter to do -- but the
        // count and every other tile have to agree with it.
        deckFilters.refresh();
    });

    slot.append(tile, star);
    return slot;
}

async function loadScenarioChoices(): Promise<ScenarioChoice[]> {
    const [sets, availablePaths] = await Promise.all([
        fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableIds = new Set(availablePaths.map(getFileName));
    const scenarioCatalog = new Map<
        string, {label: string; order: number; boxIndex: number}>();
    for (const [setName, set] of Object.entries(sets)) {
        const order = setName.match(/^(\d+)\./);
        if (!order) {
            continue;
        }
        // The order sets_info lists them in is the order the box does, so the
        // position in that array is worth keeping rather than rediscovering
        // from card numbers.
        (set.scenarios ?? []).forEach((id, boxIndex) => {
            if (availableIds.has(id) && !scenarioCatalog.has(id)) {
                scenarioCatalog.set(id, {
                    label: getProductLabel(setName, set),
                    order: Number(order[1]),
                    boxIndex,
                });
            }
        });
    }
    const scenarioIds = Array.from(scenarioCatalog.keys());

    const choices = await Promise.all(scenarioIds.map(async (id): Promise<ScenarioChoice | null> => {
        try {
            const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(id)}`);
            // Scenarios with a selectable underling have a separate villain
            // choice below. Their scenario tile should therefore show the
            // main scheme instead of duplicating the first underling's art.
            const imageSource = (data.underling_sets?.length ?? 0) > 0
                ? data.schemes
                : (data.villain?.length ? data.villain : data.schemes);
            const imageId = getFirstCardId(imageSource);
            if (!data.name || !imageId) {
                return null;
            }
            const expertId = `${id}_expert`;
            return {
                id,
                name: data.name,
                imageId,
                data,
                expertId: availableIds.has(expertId) ? expertId : null,
                productLabel: scenarioCatalog.get(id)!.label,
                productOrder: scenarioCatalog.get(id)!.order,
                boxIndex: scenarioCatalog.get(id)!.boxIndex,
            };
        } catch (error) {
            console.warn(`Failed to load scenario ${id}`, error);
            return null;
        }
    }));

    return choices.filter((choice): choice is ScenarioChoice => choice !== null);
}

async function loadHeroChoices(): Promise<HeroChoice[]> {
    const [starterPaths, userPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_user_deck?'),
    ]);
    const deckPaths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];

    const choices = await Promise.all(deckPaths.map(async ({path, isUserDeck}): Promise<HeroChoice | null> => {
        const id = getFileName(path);
        try {
            const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
            const imageId = getFirstCardId(data.hero ?? []);
            if (!data.name || !imageId) {
                return null;
            }
            return {
                id,
                name: data.deck_name ?? data.name,
                imageId,
                data,
                isUserDeck,
            };
        } catch (error) {
            console.warn(`Failed to load hero deck ${id}`, error);
            return null;
        }
    }));

    return choices
        .filter((choice): choice is HeroChoice => choice !== null)
        .sort((left, right) => {
            const groupComparison = Number(left.isUserDeck) - Number(right.isUserDeck);
            if (groupComparison !== 0) {
                return -groupComparison;
            }
            const leftName = left.data.deck_name ?? left.data.name;
            const rightName = right.data.deck_name ?? right.data.name;
            return leftName.localeCompare(rightName, undefined, {
                sensitivity: 'base',
                numeric: true,
            }) || left.id.localeCompare(right.id);
        });
}

/**
 * Pick a hero at random, then a deck for them.
 *
 * Two decisions worth stating. It shuffles heroes rather than decks: shuffling
 * decks would make a hero you have twelve netdecks for twelve times likelier
 * than one you only have the precon for, so the shape of the collection would
 * quietly decide who you play. And once a hero is drawn it always prefers a
 * synced deck, falling back to the precon only when there is none, because a
 * synced deck is one you went and got on purpose.
 *
 * Filters are overridden rather than respected -- this is for when you do not
 * want to choose, so narrowing the pool to whatever the list happened to be
 * showing would be the opposite of the point. The filter is then set to the
 * hero it landed on, so the list shows the pick rather than hiding it.
 */
function randomizeHero(): void {
    const byHero = new Map<string, HeroChoice[]>();
    for (const choice of heroChoices) {
        // A netdeck loaded into the box this session is not part of the
        // collection being shuffled.
        if (choice.isResolvedMarvelCdb) {
            continue;
        }
        const key = heroKeyOf(choice);
        byHero.set(key, [...(byHero.get(key) ?? []), choice]);
    }
    if (byHero.size === 0) {
        return;
    }

    const keys = [...byHero.keys()];
    const key = keys[Math.floor(Math.random() * keys.length)] as string;
    const forHero = byHero.get(key) as HeroChoice[];
    const synced = forHero.filter((choice) => choice.isUserDeck);
    const pool = synced.length ? synced : forHero;
    const choice = pool[Math.floor(Math.random() * pool.length)] as HeroChoice;

    leaveMarvelCdbMode();
    deckFilters.filterToHero(key);
    selectHero(choice);
}

/** The same idea for the other side of the table. */
function randomizeScenario(): void {
    if (scenarioChoices.length === 0) {
        return;
    }
    const choice = scenarioChoices[
        Math.floor(Math.random() * scenarioChoices.length)] as ScenarioChoice;
    scenarioFilters.filterToBox(choice.productLabel);
    selectScenario(choice);
}

/**
 * Draw a random option from a dropdown, as if it had been chosen.
 *
 * Placeholder options -- the empty-valued "Loading…" and "choose one" entries --
 * are not outcomes, so they are excluded rather than occasionally selected.
 */
function randomizeSelect(select: HTMLSelectElement): void {
    const options = [...select.options].filter((option) => option.value !== '');
    if (options.length === 0) {
        return;
    }
    const option = options[Math.floor(Math.random() * options.length)] as HTMLOptionElement;
    select.value = option.value;
    select.dispatchEvent(new Event('change'));
}

function heroicRules(): string[] {
    const level = Number(heroicLevel.value);
    return Number.isInteger(level) && level > 0
        ? ['v18_all', `mode_heroic_${level}`]
        : ['v18_all'];
}

function renderScenarios(choices: ScenarioChoice[]): void {
    const savedId = requestedGame.scenario || localStorage.getItem(scenarioStorageKey);
    scenarioChoices = choices;
    scenarioFilters.render(choices);

    if (requestedGame.scenario) {
        // Arriving from a coverage square, the box that square belongs to is
        // the only part of the list worth showing: sixty-odd villains is a
        // long scroll to confirm one that has already been chosen. Filtering
        // to the box also solves what showAllProducts was here for, which was
        // a remembered filter hiding the tile that arrived selected.
        const requested = choices.find((choice) => choice.id === requestedGame.scenario);
        if (requested) {
            scenarioFilters.filterToBox(requested.productLabel);
        } else {
            scenarioFilters.showAllProducts();
        }
    }

    const savedChoice = choices.find((choice) => choice.id === savedId);
    if (savedChoice) {
        selectScenario(savedChoice);
    }
    scenarioStatus.textContent = choices.length ? '' : 'No scenarios are available.';
}

function renderHeroes(choices: HeroChoice[]): void {
    const savedId = localStorage.getItem(heroStorageKey);
    heroChoices = choices;
    deckFilters.render(choices);

    // A hero asked for by id is always a precon -- the coverage grid is built
    // from the starter decks, so that is the only id it has to send. Landing on
    // the precon when you have decks of your own for that hero is not what the
    // square meant: it meant "play this hero against this villain". So the
    // precon locates the hero and then hands over to one of your decks for
    // them, preferring the one you last had selected if it is theirs.
    const requestedPrecon = requestedGame.hero
        ? choices.find((choice) => choice.id === requestedGame.hero)
        : undefined;
    const requested = (() => {
        if (!requestedPrecon) {
            return undefined;
        }
        const key = heroKeyOf(requestedPrecon);
        const mine = choices.filter(
            (choice) => choice.isUserDeck && heroKeyOf(choice) === key);
        if (!mine.length) {
            return requestedPrecon;
        }
        return mine.find((choice) => choice.id === savedId) ?? mine[0];
    })();
    const savedChoice = requested ?? choices.find((choice) => choice.id === savedId);
    if (savedChoice) {
        selectHero(savedChoice);
        // Whatever ends up selected has to be on screen. A precon arriving
        // from the coverage grid is hidden by "Hide precons", and a deck
        // remembered from last visit can be behind a hero filter set since --
        // both leave a hero named as chosen with no lit tile to show for it.
        // `requested` only for a hero a coverage square named: that is a deck
        // being asked for, so the filters give way to it. Restoring what was
        // selected last time is not, and "Favorites only" stays as it was set.
        deckFilters.revealChoice(savedChoice.id, {requested: requested !== undefined});
    }
    if (requested) {
        // Several hundred decks are unhelpful when the answer is already known,
        // so the picker opens on this hero's own.
        deckFilters.filterToHero(heroKeyOf(requested));
    }
    // The decks arrive after the picker is wired, so a page that came back in
    // aspect mode gets its dropdown filled and applied here rather than never.
    populateAspectHeroes();
    if (requestedPrecon) {
        // The aspect dropdown lists precons, so it takes the precon rather than
        // whichever of your decks was chosen above -- same hero either way.
        aspectHero.value = requestedPrecon.id;
    }
    if (deckSourceController?.getSource() === 'aspect') {
        applyAspectHero();
    }
    heroStatus.textContent = choices.length ? '' : 'No decks are available.';
}

async function initialize(): Promise<void> {
    // Restored before the scenarios land, so the first selectScenario already
    // reports the remembered set rather than flicking from Standard I to it.
    const savedHeroic = localStorage.getItem(heroicLevelStorageKey);
    if (savedHeroic
        && [...heroicLevel.options].some((option) => option.value === savedHeroic)) {
        heroicLevel.value = savedHeroic;
    }
    const savedStandardSet = localStorage.getItem(standardSetStorageKey);
    if (savedStandardSet
        && [...standardSet.options].some((option) => option.value === savedStandardSet)) {
        standardSet.value = savedStandardSet;
    }
    updateDifficulty();

    aspectDeckPicker = createAspectDeckPicker({
        onChange: () => {
            updateHeroSelection();
            updatePlayButton();
        },
    });
    void aspectDeckPicker.load();

    // Stars are drawn from the browser's copy immediately and corrected when
    // the shared list lands, which is the only thing that can add a star this
    // browser has never seen.
    onFavoritesChanged(() => deckFilters.refresh());
    void loadFavorites();

    universalDeckPicker = createUniversalDeckPicker({
        onChange: () => {
            refreshUniversalPanel();
            updatePlayButton();
        },
    });
    void universalDeckPicker.load();

    deckSourceController = createDeckSourceController({
        onChange: updatePlayButton,
        onResolved: selectResolvedMarvelCdbDeck,
        onSourceChanged: (source) => {
            // Leaving MarvelCDB mode drops the loaded deck and its pinned card,
            // whether the player went back to a precon or across to an aspect
            // deck; both keep the hero they picked from the grid.
            if (source !== 'marvelcdb') {
                leaveMarvelCdbMode();
            }
            // The tiles choose a deck, and an aspect deck replaces the deck, so
            // in aspect mode they are put away and the panel's dropdown is the
            // hero instead. Leaving them on screen was what made it unclear
            // which of the two the game would actually be played with.
            heroSection.classList.toggle('hero-decks-hidden', source === 'aspect');
            if (source === 'aspect') {
                applyAspectHero();
            }
            // The tiles stay up for a universal deck: the hero is how the deck
            // is chosen, so there is nothing else to pick.
            refreshUniversalPanel();
            updateHeroSelection();
        },
    });

    setHandMode(UserSettings.getTwoHandedSolo());
    handModeButtons.forEach((button, at) => {
        button.addEventListener('click', () => setHandMode(at === 1));
    });
    for (const button of playerTabButtons) {
        button.addEventListener('click', () => {
            switchToPlayer(Number(button.dataset.player));
        });
    }

    aspectHero.addEventListener('change', () => {
        localStorage.setItem(aspectHeroStorageKey, aspectHero.value);
        applyAspectHero();
    });

    const [scenarioResult, heroResult, beatenResult] = await Promise.allSettled([
        loadScenarioChoices(),
        loadHeroChoices(),
        loadBeatenScenarios(),
    ]);

    // Before the tiles are built, so each one is drawn with its stripe rather
    // than gaining one a moment later.
    if (beatenResult.status === 'fulfilled') {
        beatenCells = beatenResult.value;
    }

    if (scenarioResult.status === 'fulfilled') {
        renderScenarios(scenarioResult.value);
    } else {
        console.error(scenarioResult.reason);
        scenarioStatus.textContent = 'Could not load scenarios.';
    }

    if (heroResult.status === 'fulfilled') {
        renderHeroes(heroResult.value);
    } else {
        console.error(heroResult.reason);
        heroStatus.textContent = 'Could not load decks.';
    }

    updatePlayButton();
}

/**
 * What the hero in hand would take to the table right now.
 *
 * A resolved MarvelCDB deck is a whole hero deck -- the conversion keeps the
 * identity, signature cards, obligations and nemesis set from the precon and
 * replaces only the player deck. An aspect deck and a universal deck are just
 * the aspect and basic cards, so they replace the player deck and leave the
 * rest of the hero alone, which comes to the same shape.
 */
function composeHeroDeck(hero: HeroChoice): HeroData {
    const source = deckSourceController?.getSource();
    if (source === 'marvelcdb') {
        const resolved = deckSourceController?.getDeck();
        return (resolved as HeroData | null) ?? hero.data;
    }
    const prebuilt = source === 'aspect'
        ? aspectDeckPicker?.getDeck() ?? null
        : source === 'universal'
            ? currentUniversalDeck()
            : null;
    return prebuilt
        ? {...hero.data, player_deck: [...prebuilt.player_deck]}
        : hero.data;
}

/** Put what is on screen into the slot the tabs currently point at. */
function captureActiveSlot(): void {
    const source = deckSourceController?.getSource() ?? 'precon';
    playerSlots[activePlayer] = {
        hero: selectedHero,
        deck: selectedHero ? composeHeroDeck(selectedHero) : null,
        source,
        marvelCdbDeck: source === 'marvelcdb'
            ? deckSourceController?.getDeck() ?? null
            : null,
        deckLabel: selectedHero ? currentDeckLabel(selectedHero) : '',
    };
    paintPlayerTabs();
}

/** Show a slot again: the hero it holds, and the deck source it was using. */
function restoreSlot(slot: PlayerSlot): void {
    const radio = document.querySelector<HTMLInputElement>(
        `input[name="deck-source"][value="${slot.source}"]`);
    if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change', {bubbles: true}));
    }
    if (slot.hero) {
        selectHero(slot.hero, slot.source === 'marvelcdb');
    } else {
        selectedHero = null;
        markSelected(heroList, '');
        updateHeroSelection();
    }
    // A netdeck has to be pinned back into the list, or the hero it belongs to
    // is selected with nothing to show for it.
    if (slot.source === 'marvelcdb' && slot.marvelCdbDeck) {
        deckSourceController?.setDeck(slot.marvelCdbDeck, '');
    }
    updatePlayButton();
}

/**
 * One hero or two, applied to the screen rather than only remembered.
 *
 * Taking effect here and not on the next load is the point of moving it: the
 * question it answers -- who am I choosing for -- is the question this screen
 * is asking, so the answer has to change the screen.
 *
 * The hero on screen stays selected either way. Switching to one hero does not
 * discard what the other tab holds; it simply stops asking for it, and the
 * slot is still there if you switch back.
 */
function setHandMode(wanted: boolean): void {
    twoHanded = wanted;
    UserSettings.setTwoHandedSolo(wanted);
    handModeButtons.forEach((button, at) => {
        button.setAttribute('aria-pressed', String((at === 1) === wanted));
    });
    if (wanted) {
        // What is on screen belongs to whichever tab is open, and until it is
        // in that slot the summary has nothing to name for this player.
        captureActiveSlot();
    }
    paintPlayerTabs();
    updatePlayButton();
}

function paintPlayerTabs(): void {
    playerTabs.hidden = !twoHanded;
    playerTabButtons.forEach((button, player) => {
        const slot = playerSlots[player];
        const isActive = player === activePlayer;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-selected', String(isActive));
        button.classList.toggle('empty', !slot.hero && player !== activePlayer);
        const hero = player === activePlayer ? selectedHero : slot.hero;
        button.title = hero
            ? `Player ${player + 1}: ${hero.data.name}`
            : `Player ${player + 1}: no hero chosen`;
    });
}

function switchToPlayer(player: number): void {
    if (player === activePlayer || !twoHanded) {
        return;
    }
    captureActiveSlot();
    activePlayer = player;
    restoreSlot(playerSlots[player]);
    paintPlayerTabs();
    updateMatchupSummary();
}

/** Both heroes, in player order, for a two-handed game. */
function twoHandedHeroes(): Array<HeroChoice | null> {
    captureActiveSlot();
    return playerSlots.map((slot) => slot.hero);
}

async function startGame(): Promise<void> {
    if (isStarting || !selectedScenario || !selectedHero) {
        return;
    }
    const deckSource = deckSourceController?.getSource();
    const resolvedDeck = deckSource === 'marvelcdb'
        ? deckSourceController?.getDeck() ?? null
        : null;
    if (deckSource === 'marvelcdb' && !resolvedDeck) {
        return;
    }
    const aspectDeck = deckSource === 'aspect' ? aspectDeckPicker?.getDeck() ?? null : null;
    if (deckSource === 'aspect' && !aspectDeck) {
        return;
    }
    const universalDeck = currentUniversalDeck();
    if (deckSource === 'universal' && !universalDeck) {
        return;
    }

    const scenarioChoice = selectedScenario;
    const heroChoice = selectedHero;
    // A resolved MarvelCDB deck is a complete hero deck -- the conversion keeps
    // the hero, signature cards, obligations and nemesis set from the precon and
    // replaces only the player deck.
    // An aspect deck is only the aspect and basic cards, so the hero keeps its
    // own identity, signature cards, obligations and nemesis set and only the
    // player deck is replaced -- the same shape a resolved MarvelCDB deck has.
    const heroDeck = composeHeroDeck(heroChoice);
    // Two-handed sends both heroes and opens the table in the hot seat, where
    // one screen answers for whichever of them the game is asking.
    const heroDecks: HeroData[] = [];
    if (twoHanded) {
        captureActiveSlot();
        for (const slot of playerSlots) {
            if (!slot.hero || !slot.deck) {
                return;
            }
            heroDecks.push(slot.deck);
        }
    } else {
        heroDecks.push(heroDeck);
    }

    isStarting = true;
    errorMessage.textContent = '';
    playButton.textContent = 'Creating game…';
    playButton.setAttribute('aria-busy', 'true');
    updatePlayButton();

    try {
        const loadedScenario = expertMode.checked && scenarioChoice.expertId
            ? await fetchJson<ScenarioData>(
                `/get_scenario_json?${encodeURIComponent(scenarioChoice.expertId)}`,
            )
            : scenarioChoice.data;
        const scenario = structuredClone(loadedScenario);
        if ((scenario.underling_sets?.length ?? 0) > 0) {
            if (!selectedUnderling) {
                throw new Error('No underling selected');
            }
            scenario.villain = expertMode.checked
                ? selectedUnderling.data.expert_villain
                : selectedUnderling.data.villain;
            scenario.set_aside = [
                ...(scenario.set_aside ?? []),
                ...(selectedUnderling.data.set_aside ?? []),
            ];
            scenario.encounters = [
                ...(scenario.encounters ?? []),
                ...(selectedUnderling.data.encounters ?? []),
            ];
        }
        // Standard II and III replace Standard I. Substituting inside the
        // scenario's own list rather than appending is what keeps a scenario
        // dealt no Standard set at all -- Kingpin, the Wrecking Crew -- from
        // acquiring one: there is nothing there to substitute for.
        scenario.encounter_sets = (scenario.encounter_sets ?? []).map(
            (name) => (isStandardSet(name) ? standardSet.value : name));
        const encounterSetNames = Array.from(new Set([
            ...scenario.encounter_sets,
            ...(scenario.modular_sets ?? []),
        ]));

        const payload: SoloGamePayload = {
            campaign_json: JSON.stringify(scenario),
            encounter_set_names: encounterSetNames,
            hero_json: heroDecks.map((deck) => JSON.stringify(deck)),
            seed: -1,
            timeout: 0,
            challenges: [],
            // Heroic is an engine rule, not a set swap: it deals one extra
            // encounter card per player per level. Off sends nothing at all.
            rules: heroicRules(),
            campaign_log: {},
        };

        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
        window.location.assign(twoHanded ? '/table?hot_seat=1' : '/table?p=0');
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Could not create the game. Check the server log and try again.';
        isStarting = false;
        playButton.textContent = 'Play';
        playButton.removeAttribute('aria-busy');
        updatePlayButton();
    }
}

playButton.addEventListener('click', startGame);
expertMode.addEventListener('change', updateDifficulty);
standardSet.addEventListener('change', () => {
    localStorage.setItem(standardSetStorageKey, standardSet.value);
    updateDifficulty();
});
randomizeStandardSet.addEventListener('click', () => {
    // Every set, including the one already chosen: a die that cannot land on
    // the face it is showing is not a die, and rerolling until it changes
    // would quietly make Standard I likelier the more often you use it.
    const options = [...standardSet.options];
    const pick = options[Math.floor(Math.random() * options.length)];
    if (!pick) {
        return;
    }
    standardSet.value = pick.value;
    standardSet.dispatchEvent(new Event('change', {bubbles: true}));
});
heroicLevel.addEventListener('change', () => {
    localStorage.setItem(heroicLevelStorageKey, heroicLevel.value);
    updateDifficulty();
});
document.querySelector<HTMLButtonElement>('#randomize-aspect-hero')!
    .addEventListener('click', () => randomizeSelect(aspectHero));
document.querySelector<HTMLButtonElement>('#randomize-aspect-deck')!
    .addEventListener('click', () => randomizeSelect(
        document.querySelector<HTMLSelectElement>('#aspect-deck')!));
document.querySelector<HTMLButtonElement>('#randomize-hero')!
    .addEventListener('click', randomizeHero);
document.querySelector<HTMLButtonElement>('#randomize-scenario')!
    .addEventListener('click', randomizeScenario);

void initialize();
