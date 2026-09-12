import { beatenClass, beatenLabel } from './beaten.js';
import { sendToBgStats, canPushToBgStats } from './bgstats_play.js';
import { UserSettings } from './user_settings.js';

type SourceFilter = 'all'|'digital'|'physical'|'replay_import';
type TabName = 'collection'|'history'|'matchups'|'achievements';

type Overview = {
    completed: number;
    wins: number;
    losses: number;
    win_rate: number;
    unknown_games: number;
    average_rounds: number;
    average_playtime: number;
};

type RecordRow = {
    hero_code?: string;
    hero_name?: string;
    villain_code?: string;
    villain_name?: string;
    expert?: number;
    heroic?: number;
    games: number;
    wins: number;
    losses: number;
    win_rate: number;
};

type RecentGame = {
    id: number;
    finished_at: string;
    hero_code: string;
    hero_name: string;
    villain_code: string;
    villain_name: string;
    scenario_key: string;
    expert: number;
    heroic: number;
    result: 'win'|'loss'|'unknown'|'abandoned';
    rounds: number|null;
    playtime_seconds: number|null;
    source: 'digital'|'physical'|'replay_import';
    deck_name: string;
    notes: string;
    remaining_hit_points: number|null;
    minions_in_play: number|null;
    side_schemes_in_play: number|null;
    // Every seat, in order, joined by '／'; absent on rows recorded before
    // seats were kept, which are one-hero games.
    seats?: number;
    heroes?: string|null;
    decks?: string|null;
};

type Achievement = {
    id: string;
    name: string;
    description: string;
    progress: number;
    target: number;
    unlocked: boolean;
    unlocked_at: string|null;
};

type Dashboard = {
    available: boolean;
    error?: string;
    source_filter: SourceFilter;
    overview: Overview;
    heroes: RecordRow[];
    villains: RecordRow[];
    matchups: RecordRow[];
    recent_games: RecentGame[];
    achievements: Achievement[];
    owned_products: string[];
};

type SetInfo = {
    name: string;
    heroes?: string[];
    scenarios?: string[];
};

type ProductCategory = 'Core Set'|'Expansion'|'Hero Pack'|'Scenario Pack'|'Other';

type Product = {
    key: string;
    order: number;
    name: string;
    category: ProductCategory;
    heroes: string[];
    scenarios: string[];
};

type HeroData = {
    name: string;
    hero: string[];
};

type ScenarioData = {
    name: string;
    villain: string[];
    schemes: string[];
};

type GameChoice = {
    id: string;
    code: string;
    name: string;
};

function element<T extends HTMLElement>(id: string): T {
    const found = document.getElementById(id);
    if (!found) {
        throw new Error(`Missing element: ${id}`);
    }
    return found as T;
}

function escapeHtml(value: unknown): string {
    const node = document.createElement('span');
    node.textContent = String(value ?? '');
    return node.innerHTML;
}

/**
 * How hard a recorded game was, in one badge.
 *
 * Heroic is named with its level and outranks Expert, matching the coverage
 * grid: a square there shows the hardest clear, and a row here should not
 * disagree with it about what "hardest" means.
 */
function difficultyLabel(row: {expert?: number; heroic?: number}): string {
    const heroic = Number(row.heroic ?? 0);
    if (heroic > 0) {
        return row.expert ? `Expert · Heroic ${heroic}` : `Heroic ${heroic}`;
    }
    return row.expert ? 'Expert' : 'Standard';
}

function displayName(name: string|undefined, code: string|undefined): string {
    return name?.trim() || code?.trim() || 'Unknown';
}

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function firstCardId(cardIds: string[]|undefined): string {
    return cardIds?.[0]?.split(',')[0]?.trim() ?? '';
}

function humanizeId(value: string): string {
    return value.split('_').filter(Boolean).map(word =>
        word.length <= 3 && /^x?\d+$/.test(word)
            ? word.toUpperCase()
            : word.charAt(0).toUpperCase() + word.slice(1),
    ).join(' ');
}

function duration(seconds: number|null|undefined): string {
    if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
        return '—';
    }
    const totalMinutes = Math.max(0, Math.round(seconds / 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function dateTime(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.valueOf())
        ? value || '—'
        : new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(date);
}

function localDateTimeValue(value: string|Date): string {
    const date = typeof value === 'string' ? new Date(value) : value;
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

function emptyRow(columns: number, text: string): string {
    return `<tr><td class="empty-row" colspan="${columns}">${escapeHtml(text)}</td></tr>`;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(url, options);
    const body = await response.json() as T & {error?: string};
    if (!response.ok) {
        throw new Error(body.error || `${response.status} ${response.statusText}`);
    }
    return body;
}

async function postJson<T>(url: string, data: unknown): Promise<T> {
    return await fetchJson<T>(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    });
}

let currentDashboard: Dashboard|null = null;
let sourceFilter: SourceFilter = 'all';

/** The games list's day bounds, YYYY-MM-DD or '', remembered across visits. */
const GAME_DATES_KEY = 'marvel_lcg_history_game_dates';
let gamesFrom = '';
let gamesTo = '';

function readGameDates(): void {
    try {
        const stored = JSON.parse(localStorage.getItem(GAME_DATES_KEY) || '{}') as {from?: string; to?: string};
        gamesFrom = typeof stored.from === 'string' ? stored.from : '';
        gamesTo = typeof stored.to === 'string' ? stored.to : '';
    } catch {
        gamesFrom = '';
        gamesTo = '';
    }
    element<HTMLInputElement>('games-from').value = gamesFrom;
    element<HTMLInputElement>('games-to').value = gamesTo;
    element<HTMLButtonElement>('games-dates-clear').hidden = !gamesFrom && !gamesTo;
}

function saveGameDates(): void {
    try {
        localStorage.setItem(GAME_DATES_KEY, JSON.stringify({from: gamesFrom, to: gamesTo}));
    } catch {
        // Not remembering the range costs nothing but the remembering.
    }
    element<HTMLButtonElement>('games-dates-clear').hidden = !gamesFrom && !gamesTo;
}

/**
 * Which history panels are folded to their heading, remembered across visits.
 *
 * The tab stacks five sections and the one being worked in is usually the
 * last; folding the rest keeps it in reach without scrolling past them.
 */
const PANELS_KEY = 'marvel_lcg_history_panels';

function initCollapsiblePanels(): void {
    let folded: Record<string, boolean> = {};
    try {
        folded = JSON.parse(localStorage.getItem(PANELS_KEY) || '{}') as Record<string, boolean>;
    } catch {
        folded = {};
    }
    document.querySelectorAll<HTMLElement>('[data-collapsible]').forEach(panel => {
        const name = panel.dataset.collapsible!;
        const heading = panel.querySelector('.panel-heading');
        if (!heading) {
            return;
        }
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'panel-toggle';
        const apply = () => {
            const collapsed = Boolean(folded[name]);
            panel.classList.toggle('collapsed', collapsed);
            toggle.setAttribute('aria-expanded', String(!collapsed));
            toggle.title = collapsed ? 'Show this section' : 'Fold this section to its heading';
        };
        toggle.addEventListener('click', () => {
            folded[name] = !folded[name];
            try {
                localStorage.setItem(PANELS_KEY, JSON.stringify(folded));
            } catch {
                // Forgetting the fold is the only cost.
            }
            apply();
        });
        heading.appendChild(toggle);
        apply();
    });
}
let activeTab: TabName = 'matchups';

/**
 * The name a play is filed under in BG Stats.
 *
 * A setting rather than a prompt: it has to stay the same between plays for
 * BG Stats to keep matching it to the same player, and a value that matters
 * across sessions belongs somewhere it can be seen and corrected. Falls back
 * to "Me", which BG Stats will ask you to match once like any other name.
 */
function bgStatsPlayerName(): string {
    return UserSettings.getBgStatsPlayerName() || 'Me';
}

/** Empty means "let BG Stats fall back to the source name", which it does. */
function bgStatsLocation(): string {
    return UserSettings.getBgStatsLocation();
}
let setData: Record<string, SetInfo> = {};
let products: Product[] = [];
let ownedProducts = new Set<string>();
let collectionDirty = false;
let productFilter = 'All';
let heroChoices: GameChoice[] = [];
let scenarioChoices: GameChoice[] = [];
let choicesPromise: Promise<void>|null = null;

function invalidateGameChoices(): void {
    heroChoices = [];
    scenarioChoices = [];
    choicesPromise = null;
}

function renderOverview(overview: Overview): void {
    const cards: Array<[string, string]> = [
        [String(overview.completed), 'Completed games'],
        [`${overview.wins}–${overview.losses}`, 'Wins – losses'],
        [`${overview.win_rate.toFixed(1)}%`, 'Win rate'],
        [overview.average_rounds ? overview.average_rounds.toFixed(1) : '—', 'Average rounds'],
        [duration(overview.average_playtime), 'Average time'],
    ];
    element('overview').innerHTML = cards.map(([value, label]) => `
        <article class="overview-card">
            <span class="overview-value">${escapeHtml(value)}</span>
            <span class="overview-label">${escapeHtml(label)}</span>
        </article>
    `).join('');
}

function renderRecords(targetId: string, rows: RecordRow[], type: 'hero'|'villain'): void {
    const target = element<HTMLTableSectionElement>(targetId);
    if (!rows.length) {
        target.innerHTML = emptyRow(4, 'No completed games in this view.');
        return;
    }
    target.innerHTML = rows.map(row => {
        const name = type === 'hero'
            ? displayName(row.hero_name, row.hero_code)
            : displayName(row.villain_name, row.villain_code);
        return `<tr>
            <td>${escapeHtml(name)}</td>
            <td>${row.games}</td>
            <td>${row.wins}–${row.losses}</td>
            <td class="rate">${row.win_rate.toFixed(1)}%</td>
        </tr>`;
    }).join('');
}

function renderMatchups(rows: RecordRow[]): void {
    const target = element<HTMLTableSectionElement>('matchups');
    if (!rows.length) {
        target.innerHTML = emptyRow(6, 'No completed matchups in this view.');
        return;
    }
    target.innerHTML = rows.map(row => `<tr>
        <td>${escapeHtml(displayName(row.hero_name, row.hero_code))}</td>
        <td>${escapeHtml(displayName(row.villain_name, row.villain_code))}</td>
        <td><span class="difficulty ${row.heroic ? 'heroic' : row.expert ? 'expert' : ''}">${escapeHtml(difficultyLabel(row))}</span></td>
        <td>${row.games}</td>
        <td>${row.wins}–${row.losses}</td>
        <td class="rate">${row.win_rate.toFixed(1)}%</td>
    </tr>`).join('');
}

/**
 * The hero column of a game: one name, or every hero of a two-handed game
 * with a mark saying so. One person played all of them.
 */
function heroesCell(row: RecentGame): string {
    const seats = row.seats ?? 0;
    if (seats > 1 && row.heroes) {
        const names = row.heroes.split('／').map(name => escapeHtml(name.trim())).join(' &amp; ');
        return `${names} <span class="handed" title="One player, ${seats} heroes">${seats}-handed</span>`;
    }
    return escapeHtml(displayName(row.hero_name, row.hero_code));
}

function sourceLabel(source: RecentGame['source']): string {
    if (source === 'physical') return 'Physical';
    if (source === 'replay_import') return 'Replay';
    return 'Digital';
}

function renderRecent(rows: RecentGame[], unknownGames: number): void {
    const target = element<HTMLTableSectionElement>('recent-games');
    element('unknown-note').textContent = unknownGames
        ? `${unknownGames} imported replay${unknownGames === 1 ? '' : 's'} with unknown result`
        : '';
    if (!rows.length) {
        target.innerHTML = emptyRow(9, 'No game history in this view.');
        return;
    }
    target.innerHTML = rows.map(row => {
        // Only a decided game: an abandoned one has no result to record and
        // would arrive in BG Stats as a loss.
        const decided = canPushToBgStats(row);
        const push = decided
            ? `<button type="button" data-bgstats-game="${row.id}" title="Send this play to BG Stats">BG Stats</button>`
            : '';
        const edit = row.source === 'physical'
            ? `<button type="button" data-edit-game="${row.id}" title="Edit physical game">Edit</button>
               <button type="button" data-delete-game="${row.id}" class="danger" title="Delete physical game">Delete</button>`
            : '';
        const actions = push || edit
            ? `<div class="row-actions">${push}${edit}</div>`
            : '';
        return `<tr>
            <td>${escapeHtml(dateTime(row.finished_at))}</td>
            <td><span class="source ${row.source}">${escapeHtml(sourceLabel(row.source))}</span></td>
            <td>${heroesCell(row)}</td>
            <td>${escapeHtml(displayName(row.villain_name, row.villain_code))}</td>
            <td><span class="difficulty ${row.heroic ? 'heroic' : row.expert ? 'expert' : ''}">${escapeHtml(difficultyLabel(row))}</span></td>
            <td><span class="result ${escapeHtml(row.result)}">${escapeHtml(row.result)}</span></td>
            <td>${row.rounds ?? '—'}</td>
            <td>${duration(row.playtime_seconds)}</td>
            <td>${actions}</td>
        </tr>`;
    }).join('');

    target.querySelectorAll<HTMLButtonElement>('[data-bgstats-game]').forEach(button => {
        button.addEventListener('click', () => {
            const game = rows.find(row => row.id === Number(button.dataset.bgstatsGame));
            if (!game) {
                return;
            }
            sendToBgStats(game, bgStatsPlayerName(), bgStatsLocation());
        });
    });

    target.querySelectorAll<HTMLButtonElement>('[data-edit-game]').forEach(button => {
        button.addEventListener('click', () => {
            const id = Number(button.dataset.editGame);
            const game = rows.find(row => row.id === id);
            if (game) void openPhysicalGame(game);
        });
    });
    target.querySelectorAll<HTMLButtonElement>('[data-delete-game]').forEach(button => {
        button.addEventListener('click', () => void deletePhysicalGame(Number(button.dataset.deleteGame)));
    });
}

function renderAchievements(rows: Achievement[]): void {
    const unlocked = rows.filter(row => row.unlocked).length;
    element('achievement-count').textContent = `${unlocked} / ${rows.length} unlocked`;
    element('achievements').innerHTML = rows.map(row => {
        const percent = row.target ? Math.min(100, row.progress * 100 / row.target) : 0;
        const footer = row.unlocked && row.unlocked_at
            ? `Unlocked ${dateTime(row.unlocked_at)}`
            : `${row.progress} / ${row.target}`;
        return `<article class="achievement ${row.unlocked ? 'unlocked' : ''}">
            <h3>${escapeHtml(row.name)}</h3>
            <p>${escapeHtml(row.description)}</p>
            <div class="progress-track" aria-hidden="true"><span style="width:${percent}%"></span></div>
            <div class="achievement-footer"><span>${escapeHtml(footer)}</span><span>${row.unlocked ? 'Unlocked' : 'Locked'}</span></div>
        </article>`;
    }).join('');
}

function productCategory(order: number, info: SetInfo): ProductCategory {
    const heroes = info.heroes?.length ?? 0;
    const scenarios = info.scenarios?.length ?? 0;
    if (order === 1) return 'Core Set';
    if (heroes && scenarios) return 'Expansion';
    if (heroes) return 'Hero Pack';
    if (scenarios) return 'Scenario Pack';
    return 'Other';
}

function buildProducts(sets: Record<string, SetInfo>): Product[] {
    return Object.entries(sets).flatMap(([label, info]) => {
        const match = label.match(/^(\d+)\.\s*(.+)$/);
        if (!match || !info?.name) return [];
        const order = Number(match[1]);
        return [{
            key: info.name,
            order,
            name: match[2],
            category: productCategory(order, info),
            heroes: info.heroes ?? [],
            scenarios: info.scenarios ?? [],
        }];
    }).sort((left, right) => left.order - right.order);
}

function updateCollectionSummary(): void {
    element('collection-count').textContent = `${ownedProducts.size} / ${products.length} owned`;
    const saveButton = element<HTMLButtonElement>('save-collection');
    saveButton.disabled = !collectionDirty;
    saveButton.textContent = collectionDirty ? 'Save Collection' : 'Collection Saved';
}

function renderProductFilters(): void {
    const categories = ['All', 'Core Set', 'Expansion', 'Hero Pack', 'Scenario Pack', 'Other'];
    const target = element('collection-filters');
    target.innerHTML = categories.map(category => `
        <button type="button" data-category="${escapeHtml(category)}" class="${category === productFilter ? 'active' : ''}">
            ${escapeHtml(category)}
        </button>
    `).join('');
    target.querySelectorAll<HTMLButtonElement>('[data-category]').forEach(button => {
        button.addEventListener('click', () => {
            productFilter = button.dataset.category ?? 'All';
            renderProductFilters();
            renderProducts();
        });
    });
}

function renderProducts(): void {
    const query = element<HTMLInputElement>('collection-search').value.trim().toLowerCase();
    const filtered = products.filter(product => {
        const categoryMatches = productFilter === 'All' || product.category === productFilter;
        const textMatches = !query || product.name.toLowerCase().includes(query);
        return categoryMatches && textMatches;
    });
    const target = element('collection-products');
    if (!filtered.length) {
        target.innerHTML = '<p class="empty-products">No products match this filter.</p>';
        return;
    }
    target.innerHTML = filtered.map(product => {
        const owned = ownedProducts.has(product.key);
        const content: string[] = [];
        if (product.heroes.length) content.push(`${product.heroes.length} hero${product.heroes.length === 1 ? '' : 'es'}`);
        if (product.scenarios.length) content.push(`${product.scenarios.length} scenario${product.scenarios.length === 1 ? '' : 's'}`);
        return `<label class="product-card ${owned ? 'owned' : ''}">
            <input type="checkbox" data-product="${escapeHtml(product.key)}" ${owned ? 'checked' : ''}>
            <span class="product-check" aria-hidden="true">${owned ? '✓' : '+'}</span>
            <span class="product-details">
                <span class="product-type">${escapeHtml(product.category)}</span>
                <strong>${escapeHtml(product.name)}</strong>
                <small>${escapeHtml(content.join(' · ') || 'Additional content')}</small>
            </span>
        </label>`;
    }).join('');
    target.querySelectorAll<HTMLInputElement>('[data-product]').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const key = checkbox.dataset.product!;
            if (checkbox.checked) ownedProducts.add(key);
            else ownedProducts.delete(key);
            collectionDirty = true;
            invalidateGameChoices();
            renderProducts();
            updateCollectionSummary();
        });
    });
}

function renderCollection(): void {
    renderProductFilters();
    renderProducts();
    updateCollectionSummary();
}

function renderDashboard(dashboard: Dashboard): void {
    renderOverview(dashboard.overview);
    renderRecords('heroes', dashboard.heroes, 'hero');
    renderRecords('villains', dashboard.villains, 'villain');
    renderMatchups(dashboard.matchups);
    renderRecent(dashboard.recent_games, dashboard.overview.unknown_games);
    renderAchievements(dashboard.achievements);
    if (!collectionDirty) {
        ownedProducts = new Set(dashboard.owned_products);
        renderCollection();
    }
    document.querySelectorAll<HTMLButtonElement>('[data-source]').forEach(button => {
        button.classList.toggle('active', button.dataset.source === sourceFilter);
    });
}

async function loadDashboard(): Promise<void> {
    const params = new URLSearchParams({source: sourceFilter, from: gamesFrom, to: gamesTo});
    const dashboard = await fetchJson<Dashboard>(`/get_game_history?${params.toString()}`);
    if (!dashboard.available) {
        throw new Error(dashboard.error || 'Game history is unavailable.');
    }
    currentDashboard = dashboard;
    renderDashboard(dashboard);
}

type MatchupAxis = {
    id: string;
    code?: string;
    name: string;
    box: string;
    box_order: number;
};

type MatchupCell = {
    games: number;
    wins: number;
    expert_games: number;
    expert_wins: number;
    /** 0 never beaten, 1 Standard, 2 Expert, 3+ Heroic at (value - 2). */
    best_beaten: number;
    heroic_played: number;
    heroic_beaten: number;
};

type MatchupMatrix = {
    available: boolean;
    error?: string;
    heroes: MatchupAxis[];
    scenarios: MatchupAxis[];
    cells: Record<string, MatchupCell>;
};

let matchupMatrix: MatchupMatrix | null = null;

/** Re-draw the grid when the window changes size, so the squares follow it. */
function bindMatchupResize(): void {
    let resizeTimer = 0;
    window.addEventListener('resize', () => {
        // Coalesced: dragging a window edge fires this continuously and the
        // grid is a few thousand cells.
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(() => {
            if (activeTab === 'matchups' && matchupMatrix) {
                renderMatchupGrid();
            }
        }, 120);
    });
}

let matchupResizing = false;
const HERO_COLUMN_PX = 160;
/** The turned-on-its-side wave column beside the hero names. */
const WAVE_RAIL_PX = 22;
/** Small enough to still read as a square, big enough to hit. */
const MIN_CELL_PX = 13;
const MAX_CELL_PX = 34;

/** The square size that fits this many columns in the width available. */
function matchupCellSize(scenarioCount: number): number {
    const scroll = document.getElementById('matchup-scroll');
    const available = (scroll?.clientWidth ?? 0) - HERO_COLUMN_PX - WAVE_RAIL_PX - 12;
    if (available <= 0 || scenarioCount === 0) {
        return 20;
    }
    // Two pixels of border-spacing sit between every pair of columns.
    const fit = Math.floor(available / scenarioCount) - 2;
    return Math.max(MIN_CELL_PX, Math.min(MAX_CELL_PX, fit));
}

/**
 * The matchup controls, remembered between visits.
 *
 * Sorting the grid by completion is a choice about how to read it rather than
 * a one-off, and having to make it again on every visit is what made it feel
 * like the page had opinions of its own. Browser-local, like every other view
 * preference here.
 */
const MATCHUP_CONTROLS_KEY = 'marvel_lcg_matchup_controls';

type MatchupControls = {
    heroes: string;
    scenarios: string;
    counts: boolean;
    playedOnly: boolean;
};

function readMatchupControls(): Partial<MatchupControls> {
    try {
        const raw = localStorage.getItem(MATCHUP_CONTROLS_KEY);
        return raw ? JSON.parse(raw) as Partial<MatchupControls> : {};
    } catch {
        // A private window or a hand-edited value should never stop the grid
        // from drawing.
        return {};
    }
}

function writeMatchupControls(): void {
    try {
        const state: MatchupControls = {
            heroes: element<HTMLSelectElement>('matchup-sort-heroes').value,
            scenarios: element<HTMLSelectElement>('matchup-sort-scenarios').value,
            counts: element<HTMLInputElement>('matchup-counts').checked,
            playedOnly: element<HTMLInputElement>('matchup-played-only').checked,
        };
        localStorage.setItem(MATCHUP_CONTROLS_KEY, JSON.stringify(state));
    } catch {
        // Persistence is a convenience; losing it costs one dropdown.
    }
}

/** Put the remembered controls back, before the grid is first drawn. */
function restoreMatchupControls(): void {
    const saved = readMatchupControls();
    const heroSort = element<HTMLSelectElement>('matchup-sort-heroes');
    const scenarioSort = element<HTMLSelectElement>('matchup-sort-scenarios');
    // Only a value the dropdown actually offers: a mode dropped in a later
    // release would otherwise select nothing and sort by whatever that means.
    if (saved.heroes && [...heroSort.options].some(o => o.value === saved.heroes)) {
        heroSort.value = saved.heroes;
    }
    if (saved.scenarios
        && [...scenarioSort.options].some(o => o.value === saved.scenarios)) {
        scenarioSort.value = saved.scenarios;
    }
    element<HTMLInputElement>('matchup-counts').checked = saved.counts === true;
    element<HTMLInputElement>('matchup-played-only').checked = saved.playedOnly === true;
}

function renderMatchupGrid(): void {
    const table = element<HTMLTableElement>('matchup-table');
    const summary = element<HTMLElement>('matchup-summary');
    const matrix = matchupMatrix;
    if (!matrix || !matrix.available) {
        table.replaceChildren();
        summary.textContent = matrix?.error
            ?? 'Game history is unavailable, so there is nothing to compare yet.';
        return;
    }

    const sortHeroes = element<HTMLSelectElement>('matchup-sort-heroes').value;
    const sortScenarios = element<HTMLSelectElement>('matchup-sort-scenarios').value;
    const showCounts = element<HTMLInputElement>('matchup-counts').checked;
    const playedOnly = element<HTMLInputElement>('matchup-played-only').checked;
    const cellFor = (hero: MatchupAxis, scenario: MatchupAxis): MatchupCell | undefined =>
        matrix.cells[hero.code + '|' + scenario.id];

    let heroes = matrix.heroes;
    let scenarios = matrix.scenarios;
    if (playedOnly) {
        // Rows only. Dropping unplayed columns as well turned the grid into a
        // record of what has happened, when the question it exists to answer
        // is what has not -- an unplayed villain is exactly the square worth
        // seeing, and hiding it also moved every remaining column.
        heroes = heroes.filter(h => scenarios.some(s => cellFor(h, s)));
    }

    /**
     * How much of a hero's row, or a scenario's column, has been beaten.
     *
     * Beaten at any difficulty counts once: this answers "how much of the box
     * have I got through", which the header stripe does not -- that one says
     * how hard the best clear was, and the two are different questions about
     * the same line.
     *
     * Measured against the whole grid rather than what is filtered on screen,
     * so hiding rows cannot inflate a percentage.
     */
    const completionOf = (
        pairs: Array<{hero: MatchupAxis; scenario: MatchupAxis}>,
    ): number => {
        if (!pairs.length) {
            return 0;
        }
        const beaten = pairs.filter(
            ({hero, scenario}) => (cellFor(hero, scenario)?.best_beaten ?? 0) > 0).length;
        return beaten / pairs.length;
    };

    const heroCompletion = new Map(matrix.heroes.map((hero) => [
        hero.id,
        completionOf(matrix.scenarios.map((scenario) => ({hero, scenario}))),
    ]));
    const scenarioCompletion = new Map(matrix.scenarios.map((scenario) => [
        scenario.id,
        completionOf(matrix.heroes.map((hero) => ({hero, scenario}))),
    ]));

    // Re-sorted rather than animated: the grid is a few thousand squares, and
    // moving them would cost more than redrawing them.
    const byName = (left: MatchupAxis, right: MatchupAxis) =>
        left.name.localeCompare(right.name, undefined, {sensitivity: 'base'});
    const sortAxis = (
        axis: MatchupAxis[],
        mode: string,
        completion: Map<string, number>,
    ): MatchupAxis[] => {
        if (mode === 'name') {
            return [...axis].sort(byName);
        }
        if (mode === 'completion') {
            // Most complete first, and alphabetical within a tie so the
            // untouched majority does not shuffle between renders.
            return [...axis].sort((left, right) =>
                (completion.get(right.id) ?? 0) - (completion.get(left.id) ?? 0)
                || byName(left, right));
        }
        return axis;
    };

    heroes = sortAxis(heroes, sortHeroes, heroCompletion);
    scenarios = sortAxis(scenarios, sortScenarios, scenarioCompletion);

    const percent = (value: number): string => `${Math.round(value * 100)}%`;

    /**
     * Runs of neighbouring entries from the same box.
     *
     * Only meaningful while the axis is in box order, which is why the caller
     * checks the sort first: sorted by name, "Core" would appear wherever a
     * Core card happened to land and the grouping would claim an order the
     * grid is not in.
     */
    const boxRuns = (axis: MatchupAxis[]): Array<{box: string; count: number}> => {
        const runs: Array<{box: string; count: number}> = [];
        for (const entry of axis) {
            const last = runs[runs.length - 1];
            if (last && last.box === entry.box) {
                last.count += 1;
            } else {
                runs.push({box: entry.box, count: 1});
            }
        }
        return runs;
    };
    const groupHeroes = sortHeroes === 'default';
    const groupScenarios = sortScenarios === 'default';

    /**
     * The wave each hero belongs to, rather than the box they came in.
     *
     * Forty-three of the fifty-four boxes holding a hero hold exactly one, so
     * labelling every box would put a heading above nearly every row and group
     * nothing. A wave is a campaign box and the hero packs released after it,
     * which is the division that has some heroes under it: the big boxes are
     * the ones bringing more than one hero, and everything between two of them
     * belongs to the earlier.
     *
     * Scenarios need none of this -- a box brings one to five of them -- so
     * their brackets stay per box.
     */
    const waveByHero = ((): Map<string, string> => {
        const heroesPerBox = new Map<string, number>();
        for (const hero of matrix.heroes) {
            heroesPerBox.set(hero.box, (heroesPerBox.get(hero.box) ?? 0) + 1);
        }
        const waves = new Map<string, string>();
        let wave = '';
        for (const hero of [...matrix.heroes].sort((a, b) => a.box_order - b.box_order)) {
            if ((heroesPerBox.get(hero.box) ?? 0) > 1 || !wave) {
                wave = hero.box;
            }
            waves.set(hero.id, wave);
        }
        return waves;
    })();
    const waveOf = (hero: MatchupAxis): string => waveByHero.get(hero.id) ?? hero.box;

    // Counted over the full grid whatever is on screen: coverage of what you
    // have filtered down to is not the number anybody wants.
    let played = 0;
    let won = 0;
    let expertWon = 0;
    for (const hero of matrix.heroes) {
        for (const scenario of matrix.scenarios) {
            const cell = cellFor(hero, scenario);
            if (!cell) {
                continue;
            }
            played += 1;
            if (cell.wins > 0) {
                won += 1;
            }
            if (cell.expert_wins > 0) {
                expertWon += 1;
            }
        }
    }
    const possible = matrix.heroes.length * matrix.scenarios.length;
    summary.textContent = possible === 0
        ? 'No heroes or scenarios were found.'
        : `${won} of ${possible} matchups won · ${expertWon} on expert · `
            + `${played} played · ${matrix.heroes.length} heroes × `
            + `${matrix.scenarios.length} scenarios`;

    if (!heroes.length || !scenarios.length) {
        table.replaceChildren();
        const caption = document.createElement('caption');
        caption.className = 'matchup-empty';
        caption.textContent =
            'No games recorded yet. Finish a game and it will appear here.';
        table.appendChild(caption);
        return;
    }

    // Fixed layout takes its widths from the first row, so they are stated
    // outright rather than inferred from whatever the header happens to hold.
    // The square is sized to the space there is: a 62-column grid on a narrow
    // window has to scroll, but on a wide one it should use the width rather
    // than leave half the panel empty beside a fixed little grid.
    const cell = matchupCellSize(scenarios.length);
    table.style.setProperty('--matchup-cell', `${cell}px`);
    // The hero names stick just inboard of the rail, and hold the edge
    // themselves when there is no rail to sit beside.
    table.style.setProperty(
        '--matchup-wave-rail', groupHeroes ? `${WAVE_RAIL_PX}px` : '0px');
    // Measured against a layout that may not have settled: opening this tab
    // widens the shell, and the first render can run before the browser has
    // applied that. One re-measure after the next frame catches it, guarded so
    // it cannot chase its own tail.
    if (!matchupResizing) {
        matchupResizing = true;
        requestAnimationFrame(() => {
            matchupResizing = false;
            if (matchupCellSize(scenarios.length) !== cell) {
                renderMatchupGrid();
            }
        });
    }
    const columns = document.createElement('colgroup');
    if (groupHeroes) {
        // A narrow column for the wave names, turned on their side. A band
        // across the grid cost a row of height per wave and pushed the squares
        // apart; on its side it costs a little width once.
        const railColumn = document.createElement('col');
        railColumn.style.width = `${WAVE_RAIL_PX}px`;
        columns.appendChild(railColumn);
    }
    const heroColumn = document.createElement('col');
    heroColumn.style.width = `${HERO_COLUMN_PX}px`;
    columns.appendChild(heroColumn);
    for (let index = 0; index < scenarios.length; index += 1) {
        const column = document.createElement('col');
        column.style.width = `${cell}px`;
        columns.appendChild(column);
    }

    /**
     * The hardest clear anywhere along a hero's row or a scenario's column.
     *
     * A header answers "how far have I got with this one" without reading the
     * whole line -- so it takes the best of what is already in the grid rather
     * than counting anything new.
     */
    const bestAcross = (
        pairs: Array<{hero: typeof heroes[number]; scenario: typeof scenarios[number]}>,
    ): number => pairs.reduce(
        (best, {hero, scenario}) => Math.max(best, cellFor(hero, scenario)?.best_beaten ?? 0),
        0);

    const head = document.createElement('thead');
    if (groupScenarios) {
        const boxRow = document.createElement('tr');
        boxRow.className = 'matchup-box-row';
        const boxCorner = document.createElement('td');
        boxCorner.colSpan = groupHeroes ? 2 : 1;
        boxRow.appendChild(boxCorner);
        for (const run of boxRuns(scenarios.map((s) => ({...s, box: s.box})))) {
            const cell = document.createElement('th');
            cell.className = 'scenario-box';
            cell.scope = 'colgroup';
            cell.colSpan = run.count;
            cell.title = `${run.box} — ${run.count} scenarios`;
            const span = document.createElement('span');
            span.textContent = run.box;
            cell.appendChild(span);
            boxRow.appendChild(cell);
        }
        head.appendChild(boxRow);
    }
    const nameRow = document.createElement('tr');
    const nameCorner = document.createElement('td');
    nameCorner.colSpan = groupHeroes ? 2 : 1;
    nameRow.appendChild(nameCorner);
    scenarios.forEach((scenario, index) => {
        const cell = document.createElement('th');
        cell.className = 'scenario-label';
        cell.scope = 'col';
        const span = document.createElement('span');
        span.textContent = scenario.name;
        // The full name and its box, through the browser's own tooltip. A
        // hand-built panel kept getting stuck open over the grid; this one the
        // browser opens and closes itself, so it cannot.
        const bestHere = bestAcross(heroes.map((hero) => ({hero, scenario})));
        if (beatenClass(bestHere)) {
            cell.classList.add('beaten', beatenClass(bestHere));
        }
        // The column figure stays in the tooltip: these labels are rotated and
        // already truncate, so a suffix would be the first thing cut.
        cell.title = `${scenario.name} — ${scenario.box}
${beatenLabel(bestHere)}`
            + `
${percent(scenarioCompletion.get(scenario.id) ?? 0)} of heroes have beaten it`;
        cell.appendChild(span);
        nameRow.appendChild(cell);
    });
    head.appendChild(nameRow);
    table.replaceChildren(columns, head);

    const body = document.createElement('tbody');
    // How many rows each wave covers, so its label can span them.
    const waveRows = new Map<string, number>();
    if (groupHeroes) {
        for (const hero of heroes) {
            const wave = waveOf(hero);
            waveRows.set(wave, (waveRows.get(wave) ?? 0) + 1);
        }
    }
    let openBox: string | null = null;
    for (const hero of heroes) {
        const row = document.createElement('tr');
        if (groupHeroes && waveOf(hero) !== openBox) {
            openBox = waveOf(hero);
            const rail = document.createElement('th');
            rail.className = 'wave-rail';
            rail.scope = 'rowgroup';
            rail.rowSpan = waveRows.get(openBox) ?? 1;
            rail.title = `${openBox} — ${waveRows.get(openBox) ?? 1} heroes`;
            const label = document.createElement('span');
            label.textContent = openBox;
            rail.appendChild(label);
            row.appendChild(rail);
        }
        const heroCell = document.createElement('th');
        heroCell.className = 'hero-label';
        heroCell.scope = 'row';
        const heroName = document.createElement('span');
        heroName.textContent = hero.name;
        const heroPercent = document.createElement('span');
        heroPercent.className = 'coverage-percent';
        heroPercent.textContent = percent(heroCompletion.get(hero.id) ?? 0);
        const bestHere = bestAcross(scenarios.map((scenario) => ({hero, scenario})));
        if (beatenClass(bestHere)) {
            heroCell.classList.add('beaten', beatenClass(bestHere));
        }
        const heroDone = heroCompletion.get(hero.id) ?? 0;
        heroCell.title = `${hero.name} — ${hero.box}
${beatenLabel(bestHere)}`
            + `
${percent(heroDone)} of scenarios beaten`;
        heroCell.appendChild(heroName);
        heroCell.appendChild(heroPercent);
        row.appendChild(heroCell);

        scenarios.forEach((scenario, index) => {
            const cell = document.createElement('td');
            const data = cellFor(hero, scenario);
            // One square, one claim: the hardest difficulty this pairing has
            // actually been beaten at. Standard, then Expert, then Heroic by
            // level -- a harder clear replaces an easier one rather than
            // sitting beside it, so the grid reads as how far you have got.
            // Heroic beyond 4 keeps the deepest red rather than inventing
            // shades nobody would tell apart.
            const beaten = data?.best_beaten ?? 0;
            const state = !data
                ? 'none'
                : beaten >= 3 ? `won-heroic-${Math.min(beaten - 2, 4)}`
                : beaten === 2 ? 'won-expert'
                : beaten === 1 ? 'won'
                : 'lost';
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'matchup-cell ' + state;
            const record = data
                ? `${data.wins}W ${data.games - data.wins}L`
                    + (data.expert_games ? `, ${data.expert_wins}W expert` : '')
                    + (data.heroic_beaten > 0
                        ? `, beaten at Heroic ${data.heroic_beaten}`
                        : data.heroic_played > 0
                            ? `, tried at Heroic ${data.heroic_played}`
                            : '')
                : 'never played';
            button.title = `${hero.name} vs ${scenario.name} — ${record}`
                + '\nClick to set this game up';
            button.setAttribute(
                'aria-label',
                `${hero.name} versus ${scenario.name}, ${record}. Set this game up.`);
            if (data && showCounts) {
                button.textContent = String(data.games);
            }
            button.addEventListener('click', () => {
                window.location.assign(
                    '/solo?hero=' + encodeURIComponent(hero.id)
                    + '&scenario=' + encodeURIComponent(scenario.id));
            });
            cell.appendChild(button);
            row.appendChild(cell);
        });
        body.appendChild(row);
    }
    table.appendChild(body);
}

async function loadMatchupGrid(): Promise<void> {
    try {
        matchupMatrix = await fetchJson<MatchupMatrix>(
            `/get_matchup_matrix?source=${encodeURIComponent(sourceFilter)}`);
    } catch (reason) {
        matchupMatrix = {
            available: false,
            error: reason instanceof Error ? reason.message : 'Could not load the table.',
            heroes: [], scenarios: [], cells: {},
        };
    }
    renderMatchupGrid();
}

function setActiveTab(tab: TabName): void {
    activeTab = tab;
    document.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button => {
        const active = button.dataset.tab === tab;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll<HTMLElement>('[data-panel]').forEach(panel => {
        panel.hidden = panel.dataset.panel !== tab;
    });
    history.replaceState(null, '', `#${tab}`);
    // Fetched when the tab is first opened rather than with the dashboard: the
    // grid walks every starter deck and scenario file, which is wasted work for
    // anyone who never looks at it.
    if (tab === 'matchups') {
        if (matchupMatrix === null) {
            void loadMatchupGrid();
        } else {
            // The shell widens for this tab, so the squares are re-sized to the
            // width that opening it just made available.
            renderMatchupGrid();
        }
    }
}

function selectOptions(select: HTMLSelectElement, choices: GameChoice[], placeholder: string): void {
    select.replaceChildren(new Option(placeholder, ''));
    for (const choice of choices) {
        const option = new Option(choice.name, choice.id);
        option.dataset.code = choice.code;
        select.add(option);
    }
}

async function loadGameChoices(): Promise<void> {
    const [starterPaths, scenarioPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableHeroes = new Set(starterPaths.map(getFileName));
    const availableScenarios = new Set(scenarioPaths.map(getFileName));
    const ownedContent = products.filter(product => ownedProducts.has(product.key));
    const heroIds = Array.from(new Set(ownedContent.flatMap(product => product.heroes)));
    const scenarioIds = Array.from(new Set(ownedContent.flatMap(product => product.scenarios)));

    const heroes = await Promise.all(heroIds.map(async id => {
        if (!availableHeroes.has(id)) {
            return {id, code: '', name: humanizeId(id)};
        }
        try {
            const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
            return data.name ? {id, code: firstCardId(data.hero), name: data.name} : null;
        } catch (error) {
            console.warn(`Could not load hero ${id}`, error);
            return {id, code: '', name: humanizeId(id)};
        }
    }));
    const scenarios = await Promise.all(scenarioIds.map(async id => {
        if (!availableScenarios.has(id)) {
            return {id, code: '', name: humanizeId(id)};
        }
        try {
            const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(id)}`);
            const code = firstCardId(data.villain?.length ? data.villain : data.schemes);
            return data.name ? {id, code, name: data.name} : null;
        } catch (error) {
            console.warn(`Could not load scenario ${id}`, error);
            return {id, code: '', name: humanizeId(id)};
        }
    }));
    heroChoices = heroes.filter((choice): choice is GameChoice => choice !== null)
        .sort((a, b) => a.name.localeCompare(b.name));
    scenarioChoices = scenarios.filter((choice): choice is GameChoice => choice !== null)
        .sort((a, b) => a.name.localeCompare(b.name));
    selectOptions(
        element<HTMLSelectElement>('physical-hero'),
        heroChoices,
        heroChoices.length ? 'Choose a hero…' : 'No heroes in your collection',
    );
    selectOptions(
        element<HTMLSelectElement>('physical-scenario'),
        scenarioChoices,
        scenarioChoices.length ? 'Choose a scenario…' : 'No scenarios in your collection',
    );
}

async function ensureGameChoices(): Promise<void> {
    if (!choicesPromise) choicesPromise = loadGameChoices();
    await choicesPromise;
}

function selectExistingChoice(
    select: HTMLSelectElement,
    choices: GameChoice[],
    idOrKey: string,
    code: string,
    name: string,
): void {
    const found = choices.find(choice => choice.id === idOrKey || choice.code === code || choice.name === name);
    if (found) {
        select.value = found.id;
        return;
    }
    const option = new Option(name || code || 'Unknown', idOrKey || `manual_${code}`);
    option.dataset.code = code;
    select.add(option);
    select.value = option.value;
}

async function openPhysicalGame(game?: RecentGame): Promise<void> {
    await ensureGameChoices();
    const dialog = element<HTMLDialogElement>('physical-game-dialog');
    const hero = element<HTMLSelectElement>('physical-hero');
    const scenario = element<HTMLSelectElement>('physical-scenario');
    element('physical-game-error').hidden = true;
    element<HTMLInputElement>('physical-game-id').value = game ? String(game.id) : '';
    element('physical-game-title').textContent = game ? 'Edit Physical Game' : 'Log Physical Game';
    element<HTMLSelectElement>('physical-difficulty').value = game?.expert ? 'expert' : 'standard';
    element<HTMLSelectElement>('physical-heroic').value = String(game?.heroic ?? 0);
    element<HTMLSelectElement>('physical-result').value = game?.result === 'loss' ? 'loss' : 'win';
    element<HTMLInputElement>('physical-date').value = localDateTimeValue(game?.finished_at ?? new Date());
    element<HTMLInputElement>('physical-rounds').value = game?.rounds ? String(game.rounds) : '';
    element<HTMLInputElement>('physical-duration').value = game?.playtime_seconds !== null && game?.playtime_seconds !== undefined
        ? String(Math.round(game.playtime_seconds / 60)) : '';
    element<HTMLInputElement>('physical-hit-points').value = game?.remaining_hit_points !== null && game?.remaining_hit_points !== undefined
        ? String(game.remaining_hit_points) : '';
    element<HTMLInputElement>('physical-clean-table').checked = game?.minions_in_play === 0 && game?.side_schemes_in_play === 0;
    element<HTMLInputElement>('physical-deck').value = game?.deck_name ?? '';
    element<HTMLTextAreaElement>('physical-notes').value = game?.notes ?? '';
    if (game) {
        selectExistingChoice(hero, heroChoices, '', game.hero_code, game.hero_name);
        selectExistingChoice(scenario, scenarioChoices, game.scenario_key, game.villain_code, game.villain_name);
    } else {
        hero.value = '';
        scenario.value = '';
    }
    dialog.showModal();
}

function selectedChoice(select: HTMLSelectElement, choices: GameChoice[]): GameChoice {
    const selected = select.selectedOptions[0];
    if (!selected || !select.value) throw new Error('Choose both a hero and a scenario.');
    return choices.find(choice => choice.id === select.value) ?? {
        id: select.value,
        code: selected.dataset.code ?? '',
        name: selected.text,
    };
}

async function savePhysicalGame(): Promise<void> {
    const hero = selectedChoice(element<HTMLSelectElement>('physical-hero'), heroChoices);
    const scenario = selectedChoice(element<HTMLSelectElement>('physical-scenario'), scenarioChoices);
    const dateValue = element<HTMLInputElement>('physical-date').value;
    if (!dateValue) throw new Error('Played date is required.');
    const rounds = element<HTMLInputElement>('physical-rounds').value;
    const playtime = element<HTMLInputElement>('physical-duration').value;
    const remainingHitPoints = element<HTMLInputElement>('physical-hit-points').value;
    const id = element<HTMLInputElement>('physical-game-id').value;
    await postJson('/physical_games/save', {
        id: id ? Number(id) : null,
        hero_code: hero.code,
        hero_name: hero.name,
        scenario_key: scenario.id,
        villain_code: scenario.code,
        scenario_name: scenario.name,
        expert: element<HTMLSelectElement>('physical-difficulty').value === 'expert',
        heroic: Number(element<HTMLSelectElement>('physical-heroic').value) || 0,
        result: element<HTMLSelectElement>('physical-result').value,
        finished_at: new Date(dateValue).toISOString(),
        rounds: rounds ? Number(rounds) : null,
        playtime_minutes: playtime ? Number(playtime) : null,
        remaining_hit_points: remainingHitPoints ? Number(remainingHitPoints) : null,
        clean_table: element<HTMLInputElement>('physical-clean-table').checked,
        deck_name: element<HTMLInputElement>('physical-deck').value,
        notes: element<HTMLTextAreaElement>('physical-notes').value,
    });
}

async function deletePhysicalGame(id: number): Promise<void> {
    if (!window.confirm('Delete this manually logged physical game? Statistics and achievements will be recalculated.')) return;
    try {
        await postJson('/physical_games/delete', {id});
        await loadDashboard();
    } catch (reason) {
        window.alert(reason instanceof Error ? reason.message : 'Could not delete the game.');
    }
}

async function saveCollection(): Promise<void> {
    const button = element<HTMLButtonElement>('save-collection');
    button.disabled = true;
    button.textContent = 'Saving…';
    try {
        const result = await postJson<{owned_products: string[]}>('/collection/save', {
            owned_products: Array.from(ownedProducts),
        });
        ownedProducts = new Set(result.owned_products);
        collectionDirty = false;
        invalidateGameChoices();
        renderCollection();
    } catch (reason) {
        window.alert(reason instanceof Error ? reason.message : 'Could not save the collection.');
        button.disabled = false;
        button.textContent = 'Save Collection';
    }
}

type TrackerImportResult = {
    read: number;
    imported: number;
    skipped: number;
    problems: string[];
    problem_count: number;
};

async function importTrackerExport(): Promise<void> {
    const input = element<HTMLInputElement>('tracker-file');
    const button = element<HTMLButtonElement>('tracker-import');
    const status = element<HTMLElement>('tracker-status');
    const existing = document.getElementById('tracker-problems');
    existing?.remove();
    status.classList.remove('error');

    const file = input.files?.[0];
    if (!file) {
        status.textContent = 'Choose an .xlsx export from Marvel Champions Tracker first.';
        return;
    }

    button.disabled = true;
    status.textContent = `Reading ${file.name}…`;
    try {
        // Sent as base64 in JSON rather than as a multipart upload, because
        // every other write on this server is a JSON post and one export is a
        // few kilobytes.
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = '';
        for (const byte of bytes) {
            binary += String.fromCharCode(byte);
        }
        const result = await postJson<TrackerImportResult>('/import_tracker_games', {
            file: btoa(binary),
            source: element<HTMLSelectElement>('tracker-source').value,
        });

        const parts = [`${result.imported} imported`];
        if (result.skipped) {
            parts.push(`${result.skipped} already held`);
        }
        if (result.problem_count) {
            parts.push(`${result.problem_count} could not be matched`);
        }
        status.textContent = `${parts.join(' · ')} of ${result.read} plays read.`;

        if (result.problems.length) {
            const list = document.createElement('ul');
            list.id = 'tracker-problems';
            list.className = 'tracker-problems';
            for (const problem of result.problems) {
                const item = document.createElement('li');
                item.textContent = problem;
                list.appendChild(item);
            }
            status.after(list);
        }

        if (result.imported) {
            // The grid is built from this history, so it is no longer current.
            matchupMatrix = null;
            await loadDashboard();
            if (activeTab === 'matchups') {
                await loadMatchupGrid();
            }
        }
    } catch (reason) {
        status.classList.add('error');
        status.textContent = reason instanceof Error
            ? reason.message
            : 'The import failed.';
    } finally {
        button.disabled = false;
    }
}

function bindEvents(): void {
    initCollapsiblePanels();
    const reloadGames = async () => {
        saveGameDates();
        try {
            await loadDashboard();
        } catch (reason) {
            window.alert(reason instanceof Error ? reason.message : 'Could not filter game history.');
        }
    };
    element<HTMLInputElement>('games-from').addEventListener('change', event => {
        gamesFrom = (event.target as HTMLInputElement).value;
        void reloadGames();
    });
    element<HTMLInputElement>('games-to').addEventListener('change', event => {
        gamesTo = (event.target as HTMLInputElement).value;
        void reloadGames();
    });
    element<HTMLButtonElement>('games-dates-clear').addEventListener('click', () => {
        gamesFrom = '';
        gamesTo = '';
        element<HTMLInputElement>('games-from').value = '';
        element<HTMLInputElement>('games-to').value = '';
        void reloadGames();
    });
    document.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button => {
        button.addEventListener('click', () => setActiveTab(button.dataset.tab as TabName));
    });
    document.querySelectorAll<HTMLButtonElement>('[data-source]').forEach(button => {
        button.addEventListener('click', async () => {
            sourceFilter = button.dataset.source as SourceFilter;
            matchupMatrix = null;
            try {
                await loadDashboard();
                if (activeTab === 'matchups') {
                    await loadMatchupGrid();
                }
            } catch (reason) {
                window.alert(reason instanceof Error ? reason.message : 'Could not filter game history.');
            }
        });
    });
    bindMatchupResize();
    element<HTMLButtonElement>('tracker-import')
        .addEventListener('click', () => void importTrackerExport());
    for (const id of ['matchup-sort-heroes', 'matchup-sort-scenarios',
                      'matchup-counts', 'matchup-played-only']) {
        element(id).addEventListener('change', () => {
            writeMatchupControls();
            renderMatchupGrid();
        });
    }
    element<HTMLInputElement>('collection-search').addEventListener('input', renderProducts);
    element<HTMLButtonElement>('save-collection').addEventListener('click', () => void saveCollection());
    element<HTMLButtonElement>('log-game').addEventListener('click', () => void openPhysicalGame());
    element<HTMLButtonElement>('close-physical-game').addEventListener('click', () => element<HTMLDialogElement>('physical-game-dialog').close());
    element<HTMLButtonElement>('cancel-physical-game').addEventListener('click', () => element<HTMLDialogElement>('physical-game-dialog').close());
    element<HTMLFormElement>('physical-game-form').addEventListener('submit', event => {
        event.preventDefault();
        const button = element<HTMLButtonElement>('save-physical-game');
        const error = element('physical-game-error');
        button.disabled = true;
        button.textContent = 'Saving…';
        error.hidden = true;
        void savePhysicalGame().then(async () => {
            element<HTMLDialogElement>('physical-game-dialog').close();
            await loadDashboard();
            setActiveTab('history');
        }).catch(reason => {
            error.textContent = reason instanceof Error ? reason.message : 'Could not save the game.';
            error.hidden = false;
        }).finally(() => {
            button.disabled = false;
            button.textContent = 'Save Game';
        });
    });
}

async function initialize(): Promise<void> {
    const loading = element('loading');
    const error = element('error');
    const dashboardElement = element('dashboard');
    try {
        // Before anything draws: the grid is rendered as its data arrives,
        // which is earlier than the controls are bound.
        restoreMatchupControls();
        readGameDates();
        setData = await fetchJson<Record<string, SetInfo>>('/get_sets_json?');
        products = buildProducts(setData);
        await loadDashboard();
        bindEvents();
        const requestedTab = location.hash.slice(1) as TabName;
        // Matchups first: it is the tab that gets opened most, so it is the
        // one the page lands on without a hash.
        setActiveTab(
            ['collection', 'history', 'matchups', 'achievements'].includes(requestedTab)
                ? requestedTab
                : 'matchups');
        loading.hidden = true;
        dashboardElement.hidden = false;
    } catch (reason) {
        console.error(reason);
        loading.hidden = true;
        error.textContent = reason instanceof Error ? reason.message : 'Could not load the archives.';
        error.hidden = false;
    }
}

void initialize();
