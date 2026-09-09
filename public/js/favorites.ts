// Decks the player has starred, shared by Quick Game and the deck viewer.
//
// Keyed on the deck id both pages already agree on: the file name behind
// /list_user_deck and /list_starter_deck, which is what a Quick Game tile's
// dataset.id and the viewer's <option> value each carry. One list rather than
// two, so a deck starred while browsing is starred when starting a game, and a
// hero starred in Quick Game is starred in the viewer.
//
// Browser-local, like every other picker preference here. Starring is a view
// convenience rather than game data: nothing on the server needs to know, and
// a deck that stops existing simply stops being listed.

const STORAGE_KEY = 'marvel_lcg_favorite_decks';

let cache: Set<string> | null = null;

function read(): Set<string> {
    if( cache ) {
        return cache;
    }
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        cache = new Set(
            Array.isArray(parsed)
                ? parsed.filter((id): id is string => typeof id === 'string')
                : [],
        );
    } catch {
        // A private window, cleared storage, or a hand-edited value should
        // never stop a picker from rendering.
        cache = new Set();
    }
    return cache;
}

function write(ids: Set<string>): void {
    cache = ids;
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
    } catch {
        // Persistence is a convenience; losing it is not worth an error.
    }
}

// Quick Game and the viewer are frequently open in two tabs. Starring a deck
// in one leaves the other holding a stale cache, and the next redraw there
// would quietly un-star it again, so drop the cache when the key changes.
// A null key means the whole store was cleared.
window.addEventListener('storage', (event) => {
    if( event.key === STORAGE_KEY || event.key === null ) {
        cache = null;
    }
});

export function isFavorite(id: string): boolean {
    return read().has(id);
}

export function favoriteCount(): number {
    return read().size;
}

/** Star or un-star a deck, and report which it now is. */
export function toggleFavorite(id: string): boolean {
    const ids = new Set(read());
    const starred = !ids.has(id);
    if( starred ) {
        ids.add(id);
    } else {
        ids.delete(id);
    }
    write(ids);
    return starred;
}
