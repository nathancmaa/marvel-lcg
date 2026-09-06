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
    DeckSourceController,
    createDeckSourceController,
    marvelCdbDeckUrl,
} from './marvelcdb_deck.js';
import { withCardImageRevision } from './card_image_url.js';
import { DeckFilters, buildHeroLabels, createDeckFilters, heroKeyOf } from './deck_filters.js';
import { AspectDeckPicker, createAspectDeckPicker } from './aspect_decks.js';
import { ScenarioFilters, createScenarioFilters } from './scenario_filters.js';

const scenarioStorageKey = 'marvel_lcg_solo_scenario';
const heroStorageKey = 'marvel_lcg_solo_hero';
const underlingStorageKey = 'marvel_lcg_solo_underling';
const standardSetStorageKey = 'marvel_lcg_solo_standard_set';
const aspectHeroStorageKey = 'marvel_lcg_solo_aspect_hero';
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
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;
const expertMode = document.querySelector<HTMLInputElement>('#expert-mode')!;
const expertModeDescription = document.querySelector<HTMLElement>('#expert-mode-description')!;
const difficultySelection = document.querySelector<HTMLElement>('#difficulty-selection')!;
const difficultyStepNumber = document.querySelector<HTMLElement>('#difficulty-step-number')!;
const standardSet = document.querySelector<HTMLSelectElement>('#standard-set')!;
const standardSetDescription = document.querySelector<HTMLElement>('#standard-set-description')!;
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
        return button;
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
            return button;
        },
        isNew: (choice) => newScenarioIds.has(choice.id),
        onRendered: () => markSelected(scenarioList, selectedScenario?.id ?? ''),
    });

// The precon is the deck that ships with the hero; a MarvelCDB deck replaces
// only the player deck, so the hero choice stays the source of truth for the
// signature cards, obligations and nemesis set.
let deckSourceController: DeckSourceController | null = null;
let aspectDeckPicker: AspectDeckPicker | null = null;

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

function updatePlayButton(): void {
    const source = deckSourceController?.getSource();
    const awaitingDeck = (source === 'marvelcdb' && !deckSourceController?.getDeck())
        || (source === 'aspect' && !aspectDeckPicker?.getDeck());
    playButton.disabled = isStarting
        || deckSourceController?.isBusy() === true
        || !selectedScenario
        || !selectedHero
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
    standardSetDescription.textContent = dealt
        ? 'Standard II and III stand in for Standard I rather than stacking on it.'
        : 'This scenario is played without a Standard encounter set.';

    const setName = dealt
        ? standardSet.selectedOptions[0]?.text ?? 'Standard'
        : 'Standard';
    difficultySelection.textContent = expertMode.checked
        ? (dealt ? `Expert · ${setName}` : 'Expert')
        : setName;
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

async function loadScenarioChoices(): Promise<ScenarioChoice[]> {
    const [sets, availablePaths] = await Promise.all([
        fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableIds = new Set(availablePaths.map(getFileName));
    const scenarioCatalog = new Map<string, {label: string; order: number}>();
    for (const [setName, set] of Object.entries(sets)) {
        const order = setName.match(/^(\d+)\./);
        if (!order) {
            continue;
        }
        for (const id of set.scenarios ?? []) {
            if (availableIds.has(id) && !scenarioCatalog.has(id)) {
                scenarioCatalog.set(id, {
                    label: getProductLabel(setName, set),
                    order: Number(order[1]),
                });
            }
        }
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

function renderScenarios(choices: ScenarioChoice[]): void {
    const savedId = localStorage.getItem(scenarioStorageKey);
    scenarioFilters.render(choices);

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

    const savedChoice = choices.find((choice) => choice.id === savedId);
    if (savedChoice) {
        selectHero(savedChoice);
    }
    // The decks arrive after the picker is wired, so a page that came back in
    // aspect mode gets its dropdown filled and applied here rather than never.
    populateAspectHeroes();
    if (deckSourceController?.getSource() === 'aspect') {
        applyAspectHero();
    }
    heroStatus.textContent = choices.length ? '' : 'No decks are available.';
}

async function initialize(): Promise<void> {
    // Restored before the scenarios land, so the first selectScenario already
    // reports the remembered set rather than flicking from Standard I to it.
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
            updateHeroSelection();
        },
    });

    aspectHero.addEventListener('change', () => {
        localStorage.setItem(aspectHeroStorageKey, aspectHero.value);
        applyAspectHero();
    });

    const [scenarioResult, heroResult] = await Promise.allSettled([
        loadScenarioChoices(),
        loadHeroChoices(),
    ]);

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

    const scenarioChoice = selectedScenario;
    const heroChoice = selectedHero;
    // A resolved MarvelCDB deck is a complete hero deck -- the conversion keeps
    // the hero, signature cards, obligations and nemesis set from the precon and
    // replaces only the player deck.
    // An aspect deck is only the aspect and basic cards, so the hero keeps its
    // own identity, signature cards, obligations and nemesis set and only the
    // player deck is replaced -- the same shape a resolved MarvelCDB deck has.
    const heroDeck = resolvedDeck
        ?? (aspectDeck
            ? {...heroChoice.data, player_deck: [...aspectDeck.player_deck]}
            : heroChoice.data);

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
            hero_json: [JSON.stringify(heroDeck)],
            seed: -1,
            timeout: 0,
            challenges: [],
            rules: ['v18_all'],
            campaign_log: {},
        };

        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
        window.location.assign('/table?p=0');
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
void initialize();
