import { withCardImageRevision } from './card_image_url.js';
import { buildHeroLabels, compareDeckText, heroKeyOf } from './deck_filters.js';
import { CardPaperLike, describeProfile, isSubstitutable, profileCard } from './card_profile.js';
import { deckAspectsOf, suggestSubstitutes } from './card_substitution.js';

type DeckData = {
    name: string;
    deck_name?: string;
    hero: string[];
    hero_deck: string[];
    player_deck: string[];
    set_aside?: string[];
    obligations?: string[];
    nemesis_set?: string[];
    // Written by the MarvelCDB sync; absent on starter decks.
    metadata?: Record<string, string>;
};

type CardPaper = {
    card_id: string;
    pic_id?: string;
    type: string;
    name: string;
    subtitle?: string;
    desc: Record<string, string>;
    traits: string[];
    pack?: string;
};

type SetInfo = {
    name: string;
    heroes?: string[];
    scenarios?: string[];
};

type ProductInfo = {
    name: string;
    category: string;
};

type DeckChoice = {
    id: string;
    data: DeckData;
    isUserDeck: boolean;
};

type CardEntry = {
    key: string;
    cardIds: string[];
    cardId: string;
    quantity: number;
    paper: CardPaper;
};

const selectedDeckStorageKey = 'marvel_lcg_deck_viewer_deck';
const quickGameDeckStorageKey = 'marvel_lcg_solo_hero';
const groupHeroesStorageKey = 'marvel_lcg_deck_viewer_group_heroes';
const hidePreconsStorageKey = 'marvel_lcg_deck_viewer_hide_precons';

const deckSelect = document.querySelector<HTMLSelectElement>('#deck-select')!;
const groupHeroesToggle = document.querySelector<HTMLButtonElement>('#viewer-group-heroes')!;
const hidePreconsToggle = document.querySelector<HTMLButtonElement>('#viewer-hide-precons')!;
const marvelCdbLink = document.querySelector<HTMLAnchorElement>('#marvelcdb-link')!;
const deckStatus = document.querySelector<HTMLElement>('#deck-status')!;
const deckSourceBadge = document.querySelector<HTMLElement>('#deck-source-badge')!;
const deckSummary = document.querySelector<HTMLElement>('#deck-summary')!;
const deckContent = document.querySelector<HTMLElement>('#deck-content')!;
const identityImage = document.querySelector<HTMLImageElement>('#identity-image')!;
const deckHero = document.querySelector<HTMLElement>('#deck-hero')!;
const deckName = document.querySelector<HTMLElement>('#deck-name')!;
const deckCount = document.querySelector<HTMLElement>('#deck-count')!;
const deckAspects = document.querySelector<HTMLElement>('#deck-aspects')!;
const collectionGap = document.querySelector<HTMLElement>('#collection-gap')!;
const shareDeckButton = document.querySelector<HTMLButtonElement>('#share-deck')!;
const shareStatus = document.querySelector<HTMLElement>('#share-status')!;
const identityCards = document.querySelector<HTMLElement>('#identity-cards')!;
const signatureCards = document.querySelector<HTMLElement>('#signature-cards')!;
const playerCards = document.querySelector<HTMLElement>('#player-cards')!;
const encounterCards = document.querySelector<HTMLElement>('#encounter-cards')!;
const signatureCount = document.querySelector<HTMLElement>('#signature-count')!;
const playerCount = document.querySelector<HTMLElement>('#player-count')!;
const encounterCount = document.querySelector<HTMLElement>('#encounter-count')!;
const encounterSection = document.querySelector<HTMLDetailsElement>('#encounter-section')!;
const preview = document.querySelector<HTMLDialogElement>('#card-preview')!;
const previewImage = document.querySelector<HTMLImageElement>('#preview-image')!;
const previewName = document.querySelector<HTMLElement>('#preview-name')!;
const previewMeta = document.querySelector<HTMLElement>('#preview-meta')!;
const previewClose = document.querySelector<HTMLButtonElement>('#preview-close')!;
const previewFlip = document.querySelector<HTMLButtonElement>('#preview-flip')!;
const substitutePanel = document.querySelector<HTMLElement>('#substitute-panel')!;
const substituteFind = document.querySelector<HTMLButtonElement>('#substitute-find')!;
const substituteStatus = document.querySelector<HTMLElement>('#substitute-status')!;
const substituteList = document.querySelector<HTMLElement>('#substitute-list')!;

const paperCache = new Map<string, Promise<CardPaper>>();
const productsByPack = new Map<string, ProductInfo>();
let choices: DeckChoice[] = [];
let groupByHero = localStorage.getItem(groupHeroesStorageKey) === '1';
let hidePrecons = localStorage.getItem(hidePreconsStorageKey) === '1';
let previewFaces: string[] = [];
let previewFaceIndex = 0;
let currentDeck: DeckChoice | null = null;
let currentShareEntries: CardEntry[] = [];
let isCreatingShareImage = false;
// Product keys the player has marked as owned in Collection & Stats. Empty
// means no collection has been recorded, and every part of this feature
// stays hidden rather than claiming they own nothing.
let ownedProducts = new Set<string>();
// The whole card pool, needed only to suggest substitutes. It is ~2.4 MB, so
// it is fetched the first time someone asks and kept for the page's life.
let cardPoolPromise: Promise<CardPaperLike[]> | null = null;
let previewEntry: CardEntry | null = null;

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function splitCardIds(value: string): string[] {
    return value.split(',').map(id => id.trim()).filter(Boolean);
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

function getPaper(cardId: string): Promise<CardPaper> {
    const existing = paperCache.get(cardId);
    if (existing) {
        return existing;
    }
    const pending = fetchJson<CardPaper>(`/get_card_json?${encodeURIComponent(cardId)}`)
        .catch((error): CardPaper => {
            console.warn(`Failed to load card metadata ${cardId}`, error);
            return {
                card_id: cardId,
                type: 'Card',
                name: cardId,
                desc: {},
                traits: [],
            };
        });
    paperCache.set(cardId, pending);
    return pending;
}

async function loadChoices(): Promise<DeckChoice[]> {
    const [userPaths, starterPaths] = await Promise.all([
        fetchJson<string[]>('/list_user_deck?'),
        fetchJson<string[]>('/list_starter_deck?'),
    ]);
    const paths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];
    const loaded = await Promise.all(paths.map(async ({path, isUserDeck}): Promise<DeckChoice | null> => {
        const id = getFileName(path);
        try {
            const data = await fetchJson<DeckData>(`/get_hero_json?${encodeURIComponent(id)}`);
            return {id, data, isUserDeck};
        } catch (error) {
            console.warn(`Failed to load deck ${id}`, error);
            return null;
        }
    }));
    return loaded.filter((choice): choice is DeckChoice => choice !== null);
}

function loadProductCatalog(sets: Record<string, SetInfo>): void {
    productsByPack.clear();
    for (const [label, info] of Object.entries(sets)) {
        if (!info?.name) {
            continue;
        }
        const match = label.match(/^(\d+)\.\s*(.+)$/);
        const order = match ? Number(match[1]) : 0;
        const productName = match?.[2] ?? label;
        const hasHeroes = (info.heroes?.length ?? 0) > 0;
        const hasScenarios = (info.scenarios?.length ?? 0) > 0;
        let category = 'Product';
        if (order === 1 || info.name === 'core') {
            category = 'Core Set';
        } else if (hasHeroes && hasScenarios) {
            category = 'Expansion';
        } else if (hasHeroes) {
            category = 'Hero Pack';
        } else if (hasScenarios) {
            category = 'Scenario Pack';
        }
        productsByPack.set(info.name, {name: productName, category});
    }
}

function deckLabel(choice: DeckChoice): string {
    return choice.data.deck_name ?? choice.data.name;
}

/** The decks the current toggles allow, in display order. */
function visibleChoices(): DeckChoice[] {
    return choices.filter(choice => !hidePrecons || choice.isUserDeck);
}

function fillDeckSelect(): void {
    deckSelect.replaceChildren();
    const visible = visibleChoices();

    // Grouped by hero, the My decks / Starter decks split stops being the
    // organising idea, so the optgroups become hero names instead.
    const groups = new Map<string, DeckChoice[]>();
    const heroLabels = buildHeroLabels(visible);
    if (groupByHero) {
        for (const choice of visible) {
            // By identity, not name: two heroes can share one, so grouping on
            // the name put both Black Panthers under a single heading.
            const hero = heroLabels.get(heroKeyOf(choice)) ?? choice.data.name;
            const bucket = groups.get(hero);
            if (bucket) {
                bucket.push(choice);
            } else {
                groups.set(hero, [choice]);
            }
        }
    } else {
        for (const info of [
            {label: 'My decks', userDecks: true},
            {label: 'Starter decks', userDecks: false},
        ]) {
            const bucket = visible.filter(choice => choice.isUserDeck === info.userDecks);
            if (bucket.length) {
                groups.set(info.label, bucket);
            }
        }
    }

    // Hero groups are alphabetical; My decks / Starter decks keep their order.
    const labels = groupByHero
        ? [...groups.keys()].sort(compareDeckText)
        : [...groups.keys()];

    for (const label of labels) {
        const group = document.createElement('optgroup');
        group.label = label;
        const bucket = groups.get(label)!
            .slice()
            .sort((left, right) => compareDeckText(deckLabel(left), deckLabel(right)));
        for (const choice of bucket) {
            const option = document.createElement('option');
            option.value = choice.id;
            option.textContent = deckLabel(choice);
            group.appendChild(option);
        }
        deckSelect.appendChild(group);
    }
    deckSelect.disabled = visible.length === 0;
}

async function buildEntries(cardValues: string[]): Promise<CardEntry[]> {
    const grouped = new Map<string, {cardIds: string[]; quantity: number}>();
    for (const value of cardValues) {
        const cardIds = splitCardIds(value);
        const cardId = cardIds[0];
        if (!cardId) {
            continue;
        }
        const key = cardIds.join(',');
        const current = grouped.get(key);
        if (current) {
            current.quantity += 1;
        } else {
            grouped.set(key, {cardIds, quantity: 1});
        }
    }

    const entries = await Promise.all(Array.from(grouped, async ([key, value]): Promise<CardEntry> => ({
        key,
        cardIds: value.cardIds,
        cardId: value.cardIds[0],
        quantity: value.quantity,
        paper: await getPaper(value.cardIds[0]),
    })));
    return entries.sort((left, right) => {
        const typeComparison = left.paper.type.localeCompare(right.paper.type);
        return typeComparison || left.paper.name.localeCompare(right.paper.name);
    });
}

function cardMeta(paper: CardPaper): string {
    const parts = [paper.type];
    if (paper.desc.Cost !== undefined) {
        parts.push(`Cost ${paper.desc.Cost}`);
    }
    return parts.join(' · ');
}

/**
 * Which products the player owns, from Collection & Stats.
 *
 * Never throws: this is an informational overlay on a page whose real job is
 * showing a deck, so a history database that is disabled, unavailable, or
 * simply empty just means the comparison is not offered.
 */
async function loadOwnedProducts(): Promise<Set<string>> {
    try {
        const dashboard = await fetchJson<{
            available?: boolean;
            owned_products?: string[];
        }>('/get_game_history');
        if (dashboard.available === false || !Array.isArray(dashboard.owned_products)) {
            return new Set();
        }
        return new Set(dashboard.owned_products);
    } catch (error) {
        console.warn('Could not read the collection', error);
        return new Set();
    }
}

/**
 * Whether this card comes from a product the player has not marked as owned.
 *
 * Only cards belonging to a real, collectable product can count. cards.json
 * also carries `challenges`, `endless`, `status` and unpacked entries, none of
 * which are things anyone buys, and flagging those as missing would be noise.
 */
function isMissingFromCollection(paper: CardPaper): boolean {
    if (ownedProducts.size === 0) {
        return false;
    }
    const pack = paper.pack;
    if (!pack || !productsByPack.has(pack)) {
        return false;
    }
    return !ownedProducts.has(pack);
}

/** Summarise the deck against the collection, or hide the panel entirely. */
function renderCollectionGap(entries: CardEntry[]): void {
    if (ownedProducts.size === 0) {
        collectionGap.hidden = true;
        collectionGap.textContent = '';
        return;
    }

    const missingByProduct = new Map<string, number>();
    let missingCards = 0;
    for (const entry of entries) {
        if (!isMissingFromCollection(entry.paper)) {
            continue;
        }
        missingCards += entry.quantity;
        const product = productsByPack.get(entry.paper.pack!)!;
        missingByProduct.set(
            product.name, (missingByProduct.get(product.name) ?? 0) + entry.quantity);
    }

    collectionGap.hidden = false;
    if (missingCards === 0) {
        collectionGap.classList.remove('has-gap');
        collectionGap.textContent = 'You own every product this deck needs.';
        return;
    }

    const products = [...missingByProduct.entries()]
        .sort((left, right) => right[1] - left[1] || compareDeckText(left[0], right[0]))
        .map(([name, count]) => `${name} (${count})`);
    collectionGap.classList.add('has-gap');
    collectionGap.textContent =
        `${missingCards} card${missingCards === 1 ? '' : 's'} from `
        + `${missingByProduct.size} product${missingByProduct.size === 1 ? '' : 's'} `
        + `you have not marked as owned: ${products.join(', ')}.`;
}

function cardProduct(paper: CardPaper): string {
    const product = paper.pack ? productsByPack.get(paper.pack) : undefined;
    if (product) {
        return product.category === 'Core Set'
            ? product.name
            : `${product.name} · ${product.category}`;
    }
    return paper.pack ? `${paper.pack} · Product` : 'Product unavailable';
}

function sanitizeFileName(value: string): string {
    const cleaned = value
        .normalize('NFKD')
        .replace(/[^a-zA-Z0-9 _-]/g, '')
        .trim()
        .replace(/[ _]+/g, '-');
    return cleaned || 'marvel-champions-deck';
}

function loadCardImage(cardId: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
        const image = new Image();
        image.decoding = 'async';
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(`Could not load card image ${cardId}`));
        image.src = withCardImageRevision(`/${cardId}`);
    });
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
            if (blob) {
                resolve(blob);
            } else {
                reject(new Error('The browser could not create a PNG image.'));
            }
        }, 'image/png');
    });
}

function drawQuantity(
    context: CanvasRenderingContext2D,
    quantity: number,
    left: number,
    top: number,
    cardWidth: number,
): void {
    const radius = Math.round(cardWidth * 0.095);
    const centerX = left + cardWidth - radius - Math.round(cardWidth * 0.035);
    const centerY = top + radius + Math.round(cardWidth * 0.035);
    context.save();
    context.beginPath();
    context.arc(centerX, centerY, radius, 0, Math.PI * 2);
    context.fillStyle = 'rgba(5, 10, 16, 0.94)';
    context.fill();
    context.lineWidth = Math.max(3, Math.round(cardWidth * 0.012));
    context.strokeStyle = '#f4ca58';
    context.stroke();
    context.fillStyle = '#ffffff';
    context.font = `900 ${Math.round(cardWidth * 0.105)}px Arial, sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.shadowColor = '#000000';
    context.shadowBlur = 4;
    context.fillText(`×${quantity}`, centerX, centerY + 1);
    context.restore();
}

async function createShareImage(): Promise<void> {
    if (isCreatingShareImage || !currentDeck || !currentShareEntries.length) {
        return;
    }
    isCreatingShareImage = true;
    shareDeckButton.disabled = true;
    shareDeckButton.textContent = 'Creating PNG…';
    shareStatus.textContent = 'Loading card images…';

    try {
        const images = await Promise.all(currentShareEntries.map(entry => loadCardImage(entry.cardId)));
        const columns = currentShareEntries.length <= 12 ? 4 : 5;
        const cardWidth = 300;
        const cardHeight = 420;
        const gap = 10;
        const padding = 16;
        const rows = Math.ceil(currentShareEntries.length / columns);
        const canvas = document.createElement('canvas');
        canvas.width = padding * 2 + columns * cardWidth + (columns - 1) * gap;
        canvas.height = padding * 2 + rows * cardHeight + (rows - 1) * gap;
        const context = canvas.getContext('2d');
        if (!context) {
            throw new Error('Canvas is not available in this browser.');
        }

        context.fillStyle = '#09121a';
        context.fillRect(0, 0, canvas.width, canvas.height);
        images.forEach((image, index) => {
            const column = index % columns;
            const row = Math.floor(index / columns);
            const left = padding + column * (cardWidth + gap);
            const top = padding + row * (cardHeight + gap);
            context.drawImage(image, left, top, cardWidth, cardHeight);
            drawQuantity(context, currentShareEntries[index].quantity, left, top, cardWidth);
        });

        shareStatus.textContent = 'Saving image…';
        const blob = await canvasToBlob(canvas);
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = `${sanitizeFileName(currentDeck.data.deck_name ?? currentDeck.data.name)}.png`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        shareStatus.textContent = 'PNG saved to your Downloads.';
    } catch (error) {
        console.error(error);
        shareStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not create the deck image.';
    } finally {
        isCreatingShareImage = false;
        shareDeckButton.disabled = false;
        shareDeckButton.textContent = 'Share Deck';
    }
}

/** The whole card pool, fetched once and only when substitutes are asked for. */
function loadCardPool(): Promise<CardPaperLike[]> {
    if (!cardPoolPromise) {
        cardPoolPromise = fetchJson<Record<string, unknown>>('/get_cards_json?')
            .then((packs) => {
                const pool: CardPaperLike[] = [];
                for (const [pack, cards] of Object.entries(packs)) {
                    if (!Array.isArray(cards)) {
                        continue;
                    }
                    for (const card of cards as CardPaperLike[]) {
                        if (card && typeof card === 'object') {
                            pool.push({...card, pack});
                        }
                    }
                }
                return pool;
            })
            .catch((error) => {
                // Allow a later attempt rather than caching the failure.
                cardPoolPromise = null;
                throw error;
            });
    }
    return cardPoolPromise;
}

async function showSubstitutes(entry: CardEntry): Promise<void> {
    if (!currentDeck) {
        return;
    }
    substituteFind.disabled = true;
    substituteStatus.textContent = 'Looking through your collection…';
    substituteList.replaceChildren();
    try {
        const pool = await loadCardPool();
        const deckPapers = currentShareEntries.map((item) => item.paper as CardPaperLike);
        const suggestions = suggestSubstitutes({
            target: entry.paper as CardPaperLike,
            pool,
            ownedPacks: ownedProducts,
            deckAspects: deckAspectsOf(deckPapers),
            deckCardIds: new Set(currentShareEntries.map((item) => item.cardId)),
            limit: 6,
        });

        if (suggestions.length === 0) {
            substituteStatus.textContent =
                'Nothing in the products you own does a similar job.';
            return;
        }
        substituteStatus.textContent =
            'Ranked by what the card does. A starting point, not a verdict — '
            + 'only you know what this slot was for.';
        for (const suggestion of suggestions) {
            const item = document.createElement('li');
            const name = document.createElement('strong');
            const label = String(suggestion.paper.name ?? '').replace(/^\*\s*/, '');
            const cardId = String(suggestion.paper.card_id ?? '');
            // MarvelCDB addresses cards by their printed code. Guarded on the
            // shape so an id this build carries but MarvelCDB would not
            // recognise becomes plain text rather than a link to nowhere.
            if (/^\d{5}[a-z]?$/.test(cardId)) {
                const link = document.createElement('a');
                link.className = 'substitute-link';
                link.href = `https://marvelcdb.com/card/${cardId}`;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.textContent = label;
                name.appendChild(link);
            } else {
                name.textContent = label;
            }
            const why = document.createElement('span');
            why.className = 'substitute-reason';
            why.textContent = `${describeProfile(suggestion.profile)} · ${suggestion.reasons.join(', ')}`;
            item.append(name, why);
            substituteList.appendChild(item);
        }
    } catch (error) {
        console.warn('Could not suggest substitutes', error);
        substituteStatus.textContent = 'Could not read the card data.';
    } finally {
        substituteFind.disabled = false;
    }
}

function openPreview(entry: CardEntry): void {
    previewEntry = entry;
    previewFaces = entry.cardIds;
    previewFaceIndex = 0;
    previewImage.src = withCardImageRevision(`/${previewFaces[0]}`);
    previewImage.alt = entry.paper.name;
    previewName.textContent = entry.paper.name;
    previewMeta.textContent = `${cardMeta(entry.paper)} · ${cardProduct(entry.paper)}`;
    previewFlip.hidden = previewFaces.length < 2;

    // Offered only for a card you do not own, once a collection exists to
    // compare against, and only where a substitution is a coherent idea at
    // all: an identity or a signature card cannot be swapped for anything.
    substitutePanel.hidden = !isMissingFromCollection(entry.paper)
        || !isSubstitutable(profileCard(entry.paper as CardPaperLike));
    substituteStatus.textContent = '';
    substituteList.replaceChildren();
    substituteFind.disabled = false;

    preview.showModal();
}

substituteFind.addEventListener('click', () => {
    if (previewEntry) {
        void showSubstitutes(previewEntry);
    }
});

function createCardTile(entry: CardEntry): HTMLButtonElement {
    const tile = document.createElement('button');
    tile.type = 'button';
    tile.className = 'card-tile';
    tile.title = `Preview ${entry.paper.name}`;

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${entry.cardId}`);
    image.alt = entry.paper.name;
    image.loading = 'lazy';

    if (entry.quantity > 1) {
        const quantity = document.createElement('span');
        quantity.className = 'card-quantity';
        quantity.textContent = `×${entry.quantity}`;
        tile.appendChild(quantity);
    }

    const name = document.createElement('span');
    name.className = 'card-name';
    name.textContent = entry.paper.name;

    const meta = document.createElement('span');
    meta.className = 'card-meta';
    meta.textContent = cardMeta(entry.paper);

    const product = document.createElement('span');
    product.className = 'card-product';
    product.textContent = cardProduct(entry.paper);

    tile.append(image, name, meta, product);
    if (isMissingFromCollection(entry.paper)) {
        tile.classList.add('not-collected');
        const badge = document.createElement('span');
        badge.className = 'card-not-collected';
        badge.textContent = 'NOT OWNED';
        tile.appendChild(badge);
    }
    tile.addEventListener('click', () => openPreview(entry));
    return tile;
}

function renderEntries(container: HTMLElement, entries: CardEntry[]): void {
    container.replaceChildren(...entries.map(createCardTile));
}

async function showDeck(choice: DeckChoice): Promise<void> {
    deckStatus.textContent = 'Loading cards…';
    shareStatus.textContent = '';
    deckSelect.disabled = true;
    localStorage.setItem(selectedDeckStorageKey, choice.id);
    const url = new URL(window.location.href);
    url.searchParams.set('deck', choice.id);
    window.history.replaceState({}, '', url);

    try {
        const related = [
            ...(choice.data.set_aside ?? []),
            ...(choice.data.obligations ?? []),
            ...(choice.data.nemesis_set ?? []),
        ];
        const [identities, signatures, playerDeck, relatedCards] = await Promise.all([
            buildEntries(choice.data.hero ?? []),
            buildEntries(choice.data.hero_deck ?? []),
            buildEntries(choice.data.player_deck ?? []),
            buildEntries(related),
        ]);
        currentDeck = choice;
        currentShareEntries = [...identities, ...signatures, ...playerDeck];
        // Compared against the constructed deck only. The reference section is
        // the hero's own encounter cards, which come in the same box as the
        // identity and so add nothing to what you would need to buy.
        renderCollectionGap(currentShareEntries);

        renderEntries(identityCards, identities);
        renderEntries(signatureCards, signatures);
        renderEntries(playerCards, playerDeck);
        renderEntries(encounterCards, relatedCards);

        const identity = identities[0];
        identityImage.src = identity
            ? withCardImageRevision(`/${identity.cardId}`)
            : '/player';
        identityImage.alt = choice.data.name;
        deckHero.textContent = choice.data.name;
        deckName.textContent = choice.data.deck_name ?? `${choice.data.name} Starter Deck`;
        const constructedSize = choice.data.hero_deck.length + choice.data.player_deck.length;
        deckCount.textContent = `${constructedSize} cards · ${choice.data.hero_deck.length} signature · ${choice.data.player_deck.length} aspect/basic`;
        signatureCount.textContent = `${choice.data.hero_deck.length} cards`;
        playerCount.textContent = `${choice.data.player_deck.length} cards`;
        encounterCount.textContent = `${related.length} cards`;
        encounterSection.hidden = related.length === 0;

        const aspects = Array.from(new Set(playerDeck
            .map(entry => entry.paper.desc.Class)
            .filter((value): value is string => Boolean(value))));
        deckAspects.replaceChildren(...aspects.map(aspect => {
            const badge = document.createElement('span');
            badge.textContent = aspect;
            return badge;
        }));

        // Only decks synced from MarvelCDB carry a source URL; starter decks
        // and hand-made ones have nowhere to link to.
        const marvelCdbUrl = choice.data.metadata?.url;
        const isMarvelCdbUrl = typeof marvelCdbUrl === 'string'
            && /^https:\/\/marvelcdb\.com\//i.test(marvelCdbUrl);
        marvelCdbLink.hidden = !isMarvelCdbUrl;
        if (isMarvelCdbUrl) {
            marvelCdbLink.href = marvelCdbUrl;
        } else {
            marvelCdbLink.removeAttribute('href');
        }

        deckSourceBadge.hidden = false;
        deckSourceBadge.textContent = choice.isUserDeck ? 'MY DECK' : 'STARTER DECK';
        deckSourceBadge.classList.toggle('starter', !choice.isUserDeck);
        deckSummary.hidden = false;
        deckContent.hidden = false;
        deckStatus.textContent = '';
    } catch (error) {
        console.error(error);
        deckStatus.textContent = 'Could not load all cards in this deck.';
        deckSummary.hidden = true;
        deckContent.hidden = true;
        currentDeck = null;
        currentShareEntries = [];
    } finally {
        deckSelect.disabled = choices.length === 0;
    }
}

deckSelect.addEventListener('change', () => {
    const choice = choices.find(item => item.id === deckSelect.value);
    if (choice) {
        void showDeck(choice);
    }
});

function setToggle(button: HTMLButtonElement, pressed: boolean): void {
    button.setAttribute('aria-pressed', String(pressed));
    button.classList.toggle('active', pressed);
}

/** Redraw the list, keeping the open deck on screen where the toggles allow. */
function refreshDeckList(): void {
    fillDeckSelect();
    const visible = visibleChoices();
    if (!visible.length) {
        deckStatus.textContent = 'No decks match these options.';
        return;
    }
    deckStatus.textContent = '';
    if (currentDeck && visible.some(choice => choice.id === currentDeck!.id)) {
        deckSelect.value = currentDeck.id;
        return;
    }
    // Hiding precons while viewing one would otherwise leave the page showing
    // a deck that is no longer in the list, so move to the first that is.
    deckSelect.value = visible[0].id;
    void showDeck(visible[0]);
}

groupHeroesToggle.addEventListener('click', () => {
    groupByHero = !groupByHero;
    setToggle(groupHeroesToggle, groupByHero);
    localStorage.setItem(groupHeroesStorageKey, groupByHero ? '1' : '0');
    refreshDeckList();
});

hidePreconsToggle.addEventListener('click', () => {
    hidePrecons = !hidePrecons;
    setToggle(hidePreconsToggle, hidePrecons);
    localStorage.setItem(hidePreconsStorageKey, hidePrecons ? '1' : '0');
    refreshDeckList();
});

shareDeckButton.addEventListener('click', () => {
    void createShareImage();
});

previewClose.addEventListener('click', () => preview.close());
preview.addEventListener('click', (event) => {
    if (event.target === preview) {
        preview.close();
    }
});
previewFlip.addEventListener('click', () => {
    previewFaceIndex = (previewFaceIndex + 1) % previewFaces.length;
    previewImage.src = withCardImageRevision(`/${previewFaces[previewFaceIndex]}`);
});

async function initialize(): Promise<void> {
    try {
        const [loadedChoices, sets, owned] = await Promise.all([
            loadChoices(),
            fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
            loadOwnedProducts(),
        ]);
        choices = loadedChoices;
        ownedProducts = owned;
        loadProductCatalog(sets);
        setToggle(groupHeroesToggle, groupByHero);
        setToggle(hidePreconsToggle, hidePrecons);
        fillDeckSelect();
        if (!choices.length) {
            deckStatus.textContent = 'No local decks are available.';
            return;
        }
        const requestedId = new URLSearchParams(window.location.search).get('deck');
        const savedId = localStorage.getItem(selectedDeckStorageKey);
        const quickGameDeckId = localStorage.getItem(quickGameDeckStorageKey);
        // A deck named in the URL wins even when the toggles would hide it;
        // anything else falls back to what is actually listed.
        const visible = visibleChoices();
        const selected = choices.find(choice => choice.id === requestedId)
            ?? visible.find(choice => choice.id === savedId)
            ?? visible.find(choice => choice.id === quickGameDeckId)
            ?? visible.find(choice => choice.isUserDeck)
            ?? visible[0]
            ?? choices[0];
        deckSelect.value = selected.id;
        await showDeck(selected);
    } catch (error) {
        console.error(error);
        deckStatus.textContent = 'Could not load local decks.';
        deckSelect.replaceChildren();
        deckSelect.disabled = true;
    }
}

void initialize();
