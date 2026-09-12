import {
    ActiveCampaignRun,
    CampaignDefinition,
    SavedCampaign,
    campaignDefinitions,
    createInitialCampaignLog,
    getCampaignDefinition,
    getSavedCampaign,
    recordCampaignVictory,
} from './campaign_state.js';
import {
    DeckSourceController,
    createDeckSourceController,
    refreshCampaignDeck,
    saveCampaignDeck,
} from './marvelcdb_deck.js';
import { withCardImageRevision } from './card_image_url.js';
import { DeckFilters, buildHeroLabels, createDeckFilters, heroKeyOf } from './deck_filters.js';
import { AspectDeckPicker, createAspectDeckPicker } from './aspect_decks.js';

type ScenarioData = {
    name: string;
    villain: string[];
    schemes: string[];
    encounter_sets: string[];
    modular_sets: string[];
};

type HeroData = {
    name: string;
    /** The hero's name with the alter ego added when two heroes share it. */
    display_name?: string;
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
};

type HeroChoice = {
    id: string;
    name: string;
    imageId: string;
    data: HeroData;
    isUserDeck: boolean;
    isResolvedMarvelCdb?: boolean;
};

type CampaignChoice = {
    definition: CampaignDefinition;
    imageId: string;
};

type CampaignGamePayload = {
    campaign_json: string;
    encounter_set_names: string[];
    hero_json: string[];
    seed: number;
    timeout: number;
    challenges: string[];
    rules: string[];
    campaign_log: Record<string, string>;
    campaign_progress: {
        campaign: SavedCampaign;
        activeRun: ActiveCampaignRun;
        replace: boolean;
    };
};

const heroStorageKey = 'marvel_lcg_solo_hero';
const aspectHeroStorageKey = 'marvel_lcg_solo_aspect_hero';

const marvelCdbUpdate = document.querySelector<HTMLButtonElement>('#marvelcdb-update')!;

const savedCampaignSection = document.querySelector<HTMLElement>('#saved-campaign-section')!;
const savedCampaignStatus = document.querySelector<HTMLElement>('#saved-campaign-status')!;
const savedCampaignName = document.querySelector<HTMLElement>('#saved-campaign-name')!;
const savedCampaignSummary = document.querySelector<HTMLElement>('#saved-campaign-summary')!;
const resumeCampaignButton = document.querySelector<HTMLButtonElement>('#resume-campaign-button')!;
const campaignList = document.querySelector<HTMLElement>('#campaign-list')!;
const campaignStatus = document.querySelector<HTMLElement>('#campaign-status')!;
const campaignSelection = document.querySelector<HTMLElement>('#campaign-selection')!;
const scenarioSection = document.querySelector<HTMLElement>('#scenario-section')!;
const scenarioProgress = document.querySelector<HTMLElement>('#scenario-progress')!;
const scenarioPreview = document.querySelector<HTMLElement>('#scenario-preview')!;
const heroList = document.querySelector<HTMLElement>('#hero-list')!;
const heroSection = document.querySelector<HTMLElement>('#hero-section')
    ?? heroList.closest('section') as HTMLElement;
const aspectHero = document.querySelector<HTMLSelectElement>('#aspect-hero')!;
const heroStatus = document.querySelector<HTMLElement>('#hero-status')!;
const heroSelection = document.querySelector<HTMLElement>('#hero-selection')!;
const playButton = document.querySelector<HTMLButtonElement>('#play-button')!;
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;

const scenarioCache = new Map<string, ScenarioChoice>();
const campaignHeroCache = new Map<string, HeroChoice>();
let heroChoices: HeroChoice[] = [];
let selectedCampaign: CampaignDefinition | null = null;
let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let aspectDeckPicker: AspectDeckPicker | null = null;

/**
 * The deck controls, built the same way Quick Game builds them.
 *
 * A campaign picks from the same collection as a one-off game, so the picker
 * that finds a deck there should be the picker that finds it here -- sorting,
 * grouping and hiding precons included. Two pickers over one collection is one
 * of them being the good one.
 */
const deckFilters: DeckFilters<HeroChoice> = createDeckFilters<HeroChoice>({
    listHost: heroList,
    createButton: (choice) => {
        const button = createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectHero(choice),
        );
        button.classList.toggle('user-deck', choice.isUserDeck);
        return button;
    },
    // Re-drawing the list discards the selected styling, so put it back.
    onRendered: () => markSelected(heroList, selectedHero?.id ?? ''),
    // Its own, so a hero filter set here -- or by the randomiser -- does not
    // follow the player over to Quick Game and back.
    storageKey: 'marvel_lcg_campaign_deck_filters',
});
let selectedScenarioIndex = 0;
let resumedCampaign: SavedCampaign | null = null;
let isStarting = false;
let selectionRequest = 0;
let heroBeforeMarvelCdb: HeroChoice | null = null;

let deckSourceController: DeckSourceController | null = null;

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function getFirstCardId(cardIds: string[]): string {
    return cardIds[0]?.split(',')[0] ?? '';
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

async function loadScenario(scenarioId: string): Promise<ScenarioChoice> {
    const cached = scenarioCache.get(scenarioId);
    if (cached) {
        return cached;
    }

    const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(scenarioId)}`);
    const imageId = getFirstCardId(data.villain?.length ? data.villain : data.schemes);
    if (!data.name || !imageId) {
        throw new Error(`Scenario ${scenarioId} has no display data`);
    }

    const choice = { id: scenarioId, name: data.name, imageId, data };
    scenarioCache.set(scenarioId, choice);
    return choice;
}

async function loadCampaignChoices(): Promise<CampaignChoice[]> {
    const choices = await Promise.all(campaignDefinitions.map(async (definition): Promise<CampaignChoice | null> => {
        try {
            const firstScenario = await loadScenario(definition.scenarios[0]);
            return { definition, imageId: firstScenario.imageId };
        } catch (error) {
            console.warn(`Failed to load campaign ${definition.id}`, error);
            return null;
        }
    }));
    return choices.filter((choice): choice is CampaignChoice => choice !== null);
}

async function loadHeroChoice(path: string, isUserDeck: boolean): Promise<HeroChoice | null> {
    const id = getFileName(path);
    try {
        const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
        const imageId = getFirstCardId(data.hero ?? []);
        if (!data.name || !imageId) {
            return null;
        }
        return {
            id,
            name: data.deck_name ?? data.display_name ?? data.name,
            imageId,
            data,
            isUserDeck,
        };
    } catch (error) {
        console.warn(`Failed to load hero deck ${id}`, error);
        return null;
    }
}

async function loadHeroChoices(): Promise<HeroChoice[]> {
    // Frozen campaign decks are deliberately not exposed as ordinary choices.
    // They belong to one saved run and are loaded explicitly when that run is
    // resumed; otherwise a new campaign could accidentally reuse and later
    // refresh another campaign's frozen file.
    const [starterPaths, userPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_user_deck?'),
    ]);
    const deckPaths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];
    const choices = await Promise.all(deckPaths.map(
        ({path, isUserDeck}) => loadHeroChoice(path, isUserDeck)));
    return choices.filter((choice): choice is HeroChoice => choice !== null);
}

async function loadCampaignHeroChoice(heroId: string): Promise<HeroChoice | null> {
    const regularChoice = heroChoices.find((choice) => choice.id === heroId);
    if (regularChoice) {
        return regularChoice;
    }
    const cached = campaignHeroCache.get(heroId);
    if (cached) {
        return cached;
    }
    const choice = await loadHeroChoice(heroId, true);
    if (choice) {
        campaignHeroCache.set(heroId, choice);
    }
    return choice;
}

function createChoiceButton(
    id: string,
    name: string,
    imageId: string,
    onSelect: () => void,
): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice-card';
    button.dataset.id = id;
    button.setAttribute('aria-pressed', 'false');

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

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const isSelected = button.dataset.id === selectedId;
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected.toString());
    });
}

function updatePlayButton(): void {
    // A resumed campaign already has its frozen deck on disk, so it does not
    // need a freshly resolved one to start the next scenario.
    const source = deckSourceController?.getSource();
    const awaitingDeck = !resumedCampaign && (
        (source === 'marvelcdb' && !deckSourceController?.getDeck())
        || (source === 'aspect' && !aspectDeckPicker?.getDeck()));
    playButton.disabled = isStarting
        || deckSourceController?.isBusy() === true
        || !selectedCampaign
        || !selectedScenario
        || !selectedHero
        || awaitingDeck;
    if (!isStarting) {
        playButton.textContent = resumedCampaign ? 'Continue Campaign' : 'Play';
    }
}

/**
 * Offer a MarvelCDB refresh only for a campaign deck that came from MarvelCDB.
 *
 * A campaign deck is frozen once saved; between scenarios the player may
 * deliberately pull the current version, which is the one point in a run where
 * rebuilding is legal.
 */
function updateRefreshButton(): void {
    const deckId = selectedHero?.data.metadata?.marvelcdb_id;
    const isSavedCampaignDeck = resumedCampaign?.heroId === selectedHero?.id;
    marvelCdbUpdate.hidden = !(isSavedCampaignDeck && deckId);
}

function selectHero(
    choice: HeroChoice,
    keepMarvelCdbDeck = false,
    remember = true,
): void {
    if (!keepMarvelCdbDeck) {
        removeResolvedMarvelCdbChoice();
        heroBeforeMarvelCdb = null;
    }
    selectedHero = choice;
    if (remember && !choice.isResolvedMarvelCdb) {
        localStorage.setItem(heroStorageKey, choice.id);
    }
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    if (!keepMarvelCdbDeck) {
        deckSourceController?.clear();
    }
    updateRefreshButton();
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
        selectHero(previous, true, false);
    } else {
        selectedHero = null;
        heroSelection.textContent = 'Not selected';
        markSelected(heroList, '');
        updateRefreshButton();
        updatePlayButton();
    }
}

function renderScenario(choice: ScenarioChoice, definition: CampaignDefinition): void {
    scenarioSection.hidden = false;
    scenarioProgress.textContent = `Scenario ${selectedScenarioIndex + 1} of ${definition.scenarios.length}`;
    scenarioPreview.replaceChildren();

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${choice.imageId}`);
    image.alt = '';

    const details = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = choice.name;
    const text = document.createElement('p');
    text.textContent = 'The scenario is selected automatically from your campaign progress.';
    details.append(title, text);
    scenarioPreview.append(image, details);
}

async function selectCampaign(
    definition: CampaignDefinition,
    saved: SavedCampaign | null,
): Promise<void> {
    const request = ++selectionRequest;
    selectedCampaign = definition;
    resumedCampaign = saved;
    updateRefreshButton();

    // A resumed run may select a frozen deck that is intentionally absent from
    // the normal grid. When the player switches back to starting a new
    // campaign, restore the last ordinary choice instead of leaking that
    // frozen deck into the new run.
    if (!saved && selectedHero && !heroChoices.some((choice) => choice.id === selectedHero?.id)) {
        const regularHero = heroChoices.find(
            (choice) => choice.id === localStorage.getItem(heroStorageKey));
        if (regularHero) {
            selectHero(regularHero);
        } else {
            selectedHero = null;
            heroSelection.textContent = 'Not selected';
            markSelected(heroList, '');
            updateRefreshButton();
        }
    }
    selectedScenario = null;
    selectedScenarioIndex = Math.min(
        Math.max(saved?.scenarioIndex ?? 0, 0),
        definition.scenarios.length - 1,
    );
    campaignSelection.textContent = definition.name;
    markSelected(campaignList, definition.id);
    scenarioSection.hidden = false;
    scenarioPreview.textContent = 'Loading scenario…';
    errorMessage.textContent = '';
    updatePlayButton();

    try {
        const scenario = await loadScenario(definition.scenarios[selectedScenarioIndex]);
        if (request !== selectionRequest) {
            return;
        }
        selectedScenario = scenario;
        renderScenario(scenario, definition);

        if (saved?.heroId) {
            const savedHero = await loadCampaignHeroChoice(saved.heroId);
            if (request !== selectionRequest) {
                return;
            }
            if (savedHero) {
                // Do not persist a run-specific file as the user's ordinary
                // deck choice. It must only be selected by this resume path.
                selectHero(savedHero, false, false);
            } else {
                selectedHero = null;
                heroSelection.textContent = 'Saved campaign deck not found';
                markSelected(heroList, '');
                throw new Error(`Saved campaign deck ${saved.heroId} was not found`);
            }
        }
    } catch (error) {
        console.error(error);
        if (request === selectionRequest) {
            scenarioPreview.textContent = 'Could not load the current scenario.';
            errorMessage.textContent = 'Could not load this campaign.';
        }
    }
    updatePlayButton();
}

function renderCampaigns(choices: CampaignChoice[]): void {
    campaignList.replaceChildren();
    for (const choice of choices) {
        campaignList.appendChild(createChoiceButton(
            choice.definition.id,
            choice.definition.name,
            choice.imageId,
            () => void selectCampaign(choice.definition, null),
        ));
    }
    campaignStatus.textContent = choices.length ? '' : 'No campaigns are available.';
}

/**
 * Pick a hero at random, then one of their decks.
 *
 * Identical to Quick Game's rule, deliberately: heroes are shuffled rather
 * than decks, so a hero you have a dozen netdecks for is no likelier than one
 * you have a single deck for, and a synced deck beats the precon where both
 * exist. Two randomisers disagreeing about what a fair draw is would be worse
 * than either.
 */
/** The precon deck for whichever hero a choice belongs to. */
function preconFor(choice: HeroChoice | null): string {
    if (!choice) {
        return '';
    }
    const key = heroKeyOf(choice);
    return heroChoices.find(
        (other) => !other.isUserDeck && heroKeyOf(other) === key)?.id ?? '';
}

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
        // Falling back to the hero already picked keeps switching into aspect
        // mode from silently changing who is playing.
        : (preconFor(selectedHero) || options[0]?.id) ?? '';
}

/** Make the aspect panel's dropdown the selected hero. */
function applyAspectHero(): void {
    const choice = heroChoices.find((item) => item.id === aspectHero.value);
    if (choice) {
        selectHero(choice);
    }
}

/**
 * Draw a random option from a dropdown, as if it had been chosen.
 *
 * The empty "Loading…" and unset entries are not outcomes, so they are left
 * out rather than occasionally drawn.
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

function randomizeHero(): void {
    const byHero = new Map<string, HeroChoice[]>();
    for (const choice of heroChoices) {
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

    deckFilters.filterToHero(key);
    selectHero(choice);
}

function renderHeroes(choices: HeroChoice[]): void {
    heroChoices = choices;
    deckFilters.render(choices);

    const savedHeroId = localStorage.getItem(heroStorageKey);
    const savedHero = choices.find((choice) => choice.id === savedHeroId);
    if (savedHero) {
        selectHero(savedHero);
        // Same reason as Quick Game: a remembered deck must not be selected
        // behind a filter that hides it.
        deckFilters.revealChoice(savedHero.id);
    }
    populateAspectHeroes();
    if (deckSourceController?.getSource() === 'aspect') {
        applyAspectHero();
    }
    heroStatus.textContent = choices.length ? '' : 'No decks are available.';
}

async function renderSavedCampaign(saved: SavedCampaign | null): Promise<void> {
    if (!saved) {
        savedCampaignSection.hidden = true;
        return;
    }

    const definition = getCampaignDefinition(saved.campaignId);
    if (!definition) {
        savedCampaignSection.hidden = true;
        return;
    }

    const scenarioIndex = Math.min(Math.max(saved.scenarioIndex, 0), definition.scenarios.length - 1);
    const scenario = await loadScenario(definition.scenarios[scenarioIndex]);
    const savedHero = await loadCampaignHeroChoice(saved.heroId);
    const savedHeroName = savedHero?.name ?? 'Saved deck not found';
    savedCampaignSection.hidden = false;
    savedCampaignName.textContent = definition.name;
    savedCampaignStatus.textContent = saved.completed ? 'Completed' : `Scenario ${scenarioIndex + 1} of ${definition.scenarios.length}`;
    savedCampaignSummary.textContent = saved.completed
        ? `Completed with ${savedHeroName}.`
        : `${scenario.name} · ${savedHeroName}`;
    resumeCampaignButton.hidden = saved.completed;
    resumeCampaignButton.onclick = () => void selectCampaign(definition, saved);
}

async function refreshSelectedCampaignDeck(): Promise<void> {
    const heroId = selectedHero?.id;
    if (!heroId || marvelCdbUpdate.disabled) {
        return;
    }

    marvelCdbUpdate.disabled = true;
    const previousLabel = marvelCdbUpdate.textContent;
    marvelCdbUpdate.textContent = 'Updating…';
    errorMessage.textContent = '';

    try {
        const result = await refreshCampaignDeck(heroId);
        const choice = heroChoices.find((entry) => entry.id === heroId);
        if (choice) {
            choice.data = result.deck as HeroData;
        }
        // Silent success reads the same as a no-op, so say what moved.
        errorMessage.textContent = result.changed === 0
            ? 'Deck is already up to date.'
            : `Updated — ${result.changed} card${result.changed === 1 ? '' : 's'} changed.`;
    } catch (error) {
        errorMessage.textContent = error instanceof Error
            ? error.message
            : 'Could not update that deck from MarvelCDB.';
    } finally {
        marvelCdbUpdate.disabled = false;
        marvelCdbUpdate.textContent = previousLabel;
    }
}

async function initialize(): Promise<void> {
    aspectDeckPicker = createAspectDeckPicker({onChange: updatePlayButton});
    void aspectDeckPicker.load();

    deckSourceController = createDeckSourceController({
        onChange: updatePlayButton,
        onResolved: selectResolvedMarvelCdbDeck,
        onSourceChanged: (source) => {
            if (source !== 'marvelcdb') {
                leaveMarvelCdbMode();
            }
            // The tiles choose a deck, and an aspect deck replaces the deck, so
            // in aspect mode they are put away and the panel's dropdown decides
            // who is playing.
            heroSection.classList.toggle('hero-decks-hidden', source === 'aspect');
            if (source === 'aspect') {
                applyAspectHero();
            }
            updatePlayButton();
        },
    });
    aspectHero.addEventListener('change', () => {
        localStorage.setItem(aspectHeroStorageKey, aspectHero.value);
        applyAspectHero();
    });
    document.querySelector<HTMLButtonElement>('#randomize-aspect-hero')
        ?.addEventListener('click', () => randomizeSelect(aspectHero));
    document.querySelector<HTMLButtonElement>('#randomize-aspect-deck')
        ?.addEventListener('click', () => randomizeSelect(
            document.querySelector<HTMLSelectElement>('#aspect-deck')!));
    marvelCdbUpdate.addEventListener('click', () => void refreshSelectedCampaignDeck());
    document.querySelector<HTMLButtonElement>('#randomize-hero')
        ?.addEventListener('click', randomizeHero);

    const [campaignResult, heroResult] = await Promise.allSettled([
        loadCampaignChoices(),
        loadHeroChoices(),
    ]);

    if (campaignResult.status === 'fulfilled') {
        renderCampaigns(campaignResult.value);
    } else {
        console.error(campaignResult.reason);
        campaignStatus.textContent = 'Could not load campaigns.';
    }

    if (heroResult.status === 'fulfilled') {
        renderHeroes(heroResult.value);
    } else {
        console.error(heroResult.reason);
        heroStatus.textContent = 'Could not load decks.';
    }

    try {
        await recordCampaignVictory();
        await renderSavedCampaign(await getSavedCampaign());
    } catch (error) {
        console.error(error);
        savedCampaignSection.hidden = true;
    }
    updatePlayButton();
}

async function startGame(): Promise<void> {
    if (isStarting || !selectedCampaign || !selectedScenario || !selectedHero) {
        return;
    }

    let existingSave: SavedCampaign | null;
    try {
        existingSave = await getSavedCampaign();
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Could not read campaign progress from the server.';
        return;
    }
    if (
        !resumedCampaign &&
        existingSave &&
        !existingSave.completed &&
        !window.confirm('Starting a new campaign will replace the currently saved campaign. Continue?')
    ) {
        return;
    }

    isStarting = true;
    errorMessage.textContent = '';
    playButton.textContent = 'Creating campaign game…';
    playButton.setAttribute('aria-busy', 'true');
    updatePlayButton();

    // A MarvelCDB deck becomes a file for the run: campaigns persist their hero
    // as a deck id, and freezing it is what stops the deck drifting between
    // scenarios without the player asking.
    let heroDeck: HeroData = selectedHero.data;
    let heroId = selectedHero.id;
    const resolvedDeck = deckSourceController?.getSource() === 'marvelcdb'
        ? deckSourceController.getDeck()
        : null;
    // An aspect deck is only the aspect and basic cards, so the hero keeps its
    // identity, signature cards, obligations and nemesis set and only the
    // player deck is replaced -- the same shape a resolved MarvelCDB deck has,
    // which is why it is frozen for the run the same way.
    const aspectDeck = deckSourceController?.getSource() === 'aspect'
        ? aspectDeckPicker?.getDeck() ?? null
        : null;
    const deckToFreeze = resolvedDeck ?? (aspectDeck
        ? {...selectedHero.data, player_deck: [...aspectDeck.player_deck]}
        : null);
    if (deckToFreeze) {
        try {
            const stored = await saveCampaignDeck(selectedCampaign.id, deckToFreeze);
            heroDeck = stored.deck as HeroData;
            heroId = stored.hero_id;
        } catch (error) {
            console.error(error);
            errorMessage.textContent = error instanceof Error
                ? error.message
                : 'Could not save that deck for the campaign.';
            isStarting = false;
            playButton.removeAttribute('aria-busy');
            updatePlayButton();
            return;
        }
    }

    const campaignLog = resumedCampaign?.campaignLog ?? createInitialCampaignLog(selectedCampaign.id);
    const scenarioData = {
        ...selectedScenario.data,
        campaign_id: selectedCampaign.id,
    };
    const encounterSetNames = Array.from(new Set([
        ...(selectedScenario.data.encounter_sets ?? []),
        ...(selectedScenario.data.modular_sets ?? []),
    ]));
    const saved: SavedCampaign = {
        version: 1,
        campaignId: selectedCampaign.id,
        scenarioIndex: selectedScenarioIndex,
        heroId,
        campaignLog,
        completed: false,
        updatedAt: new Date().toISOString(),
    };
    const activeRun: ActiveCampaignRun = {
        version: 1,
        campaignId: selectedCampaign.id,
        scenarioId: selectedScenario.id,
        scenarioName: selectedScenario.name,
        scenarioIndex: selectedScenarioIndex,
    };
    const payload: CampaignGamePayload = {
        campaign_json: JSON.stringify(scenarioData),
        encounter_set_names: encounterSetNames,
        hero_json: [JSON.stringify(heroDeck)],
        seed: -1,
        timeout: 0,
        challenges: [],
        rules: [
            'mode_campaign',
            'v18_all',
        ],
        campaign_log: campaignLog,
        campaign_progress: {
            campaign: saved,
            activeRun,
            replace: resumedCampaign === null,
        },
    };

    try {
        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            const result = await response.json().catch(() => null) as {error?: string} | null;
            throw new Error(result?.error ?? `${response.status} ${response.statusText}`);
        }
        window.location.assign('/table?p=0');
    } catch (error) {
        console.error(error);
        errorMessage.textContent = error instanceof Error
            ? error.message
            : 'Could not create the campaign game. Check the server log and try again.';
        isStarting = false;
        playButton.removeAttribute('aria-busy');
        updatePlayButton();
    }
}

playButton.addEventListener('click', startGame);
void initialize();
