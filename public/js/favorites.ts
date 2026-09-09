// Decks the player has starred, shared by Quick Game and the deck viewer.
//
// Keyed on the deck id both pages already agree on: the file name behind
// /list_user_deck and /list_starter_deck, which is what a Quick Game tile's
// dataset.id and the viewer's <option> value each carry. One list rather than
// two, so a deck starred while browsing is starred when starting a game, and a
// hero starred in Quick Game is starred in the viewer.
//
// The list lives on the server, beside the collection and for the same reason:
// one container is played from a laptop, a phone and a tablet, and a star set
// on one of them meant nothing on the others. What is kept in the browser is a
// copy, not the truth -- it paints the stars before the request lands, and
// stands in when the request does not.

const STORAGE_KEY = 'marvel_lcg_favorite_decks';

type FavoritesResponse = {
    available: boolean;
    favorite_decks?: string[];
};

let cache: Set<string> | null = null;
let listeners: Array<() => void> = [];

function readStorage(): Set<string> {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        return new Set(
            Array.isArray(parsed)
                ? parsed.filter((id): id is string => typeof id === 'string')
                : [],
        );
    } catch {
        // A private window, cleared storage, or a hand-edited value should
        // never stop a picker from rendering.
        return new Set();
    }
}

function writeStorage(ids: Set<string>): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
    } catch {
        // The browser copy is a convenience; losing it costs a redraw.
    }
}

function current(): Set<string> {
    if (!cache) {
        cache = readStorage();
    }
    return cache;
}

function announce(): void {
    for (const listener of listeners) {
        listener();
    }
}

// Two tabs on one browser still share storage, and the one that did not make
// the change would otherwise redraw from a stale cache and un-star the deck.
window.addEventListener('storage', (event) => {
    if( event.key === STORAGE_KEY || event.key === null ) {
        cache = null;
        announce();
    }
});

export function isFavorite(id: string): boolean {
    return current().has(id);
}

export function favoriteCount(): number {
    return current().size;
}

/** Redraw whatever shows a star when the list changes underneath it. */
export function onFavoritesChanged(listener: () => void): void {
    listeners.push(listener);
}

/**
 * Fetch the shared list and adopt it.
 *
 * The server is the truth, so what comes back replaces the browser's copy
 * outright -- including dropping a star this browser thinks it has. A failed
 * request changes nothing and leaves the local copy in charge, which is what
 * keeps the stars working when history is switched off.
 */
export async function loadFavorites(): Promise<void> {
    try {
        const response = await fetch('/get_favorite_decks?');
        if( !response.ok ) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
        const data = await response.json() as FavoritesResponse;
        if( !data.available || !Array.isArray(data.favorite_decks) ) {
            return;
        }
        cache = new Set(data.favorite_decks);
        writeStorage(cache);
        announce();
    } catch (error) {
        console.warn('Could not load the favourite decks', error);
    }
}

/**
 * Star or un-star a deck, and report which it now is.
 *
 * The change lands locally first and is sent afterwards: starring a deck is a
 * click on a tile, and waiting for a round trip to fill the star in would be
 * felt on every one of them. If the send fails the browser keeps the change,
 * so nothing is lost from under the player -- it simply has not travelled yet.
 */
export function toggleFavorite(id: string): boolean {
    const ids = new Set(current());
    const starred = !ids.has(id);
    if( starred ) {
        ids.add(id);
    } else {
        ids.delete(id);
    }
    cache = ids;
    writeStorage(ids);
    void save(ids);
    return starred;
}

async function save(ids: Set<string>): Promise<void> {
    try {
        const response = await fetch('/favorites/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({favorite_decks: [...ids]}),
        });
        if( !response.ok ) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
    } catch (error) {
        console.warn('Could not save the favourite decks', error);
    }
}
