import {
    ANIMATION_TIME_DEFAULT,
    DEFAULT_OPTION_KEYS,
    UserSettings,
} from './user_settings.js'
import { whatKeyDoes } from './game_keys.js'

const animationTime = document.getElementById('animation-time') as HTMLInputElement
const animationTimeValue = document.getElementById('animation-time-value') as HTMLOutputElement
const autoSaveReplays = document.getElementById('autosave-replays') as HTMLInputElement
const skipSingleTargetConfirm = document.getElementById('skip-single-target-confirm') as HTMLInputElement
const confirmKey = document.getElementById('confirm-key') as HTMLInputElement
const denyKey = document.getElementById('deny-key') as HTMLInputElement
const undoKey = document.getElementById('undo-key') as HTMLInputElement
const optionKeysRow = document.getElementById('option-keys') as HTMLElement
const optionKeysReset = document.getElementById('option-keys-reset') as HTMLButtonElement
const optionKeyWarning = document.getElementById('option-key-warning') as HTMLElement

/**
 * The boxes for the option keys, one per position, built to match storage.
 *
 * Declared up here with the other elements rather than beside the code that
 * reads it: updateKeyWarning runs from the init block below, and a const is
 * not hoisted the way a function declaration is.
 */
const optionKeyBoxes: HTMLInputElement[] = DEFAULT_OPTION_KEYS.map((_, at) => {
    const slot = document.createElement('span')
    slot.className = 'option-slot'

    const number = document.createElement('span')
    number.className = 'option-slot-number'
    number.textContent = String(at + 1)

    const box = document.createElement('input')
    box.type = 'text'
    box.className = 'key-box'
    box.readOnly = true
    box.autocomplete = 'off'
    box.title = `The key for the ${at + 1}${['st', 'nd', 'rd'][at] ?? 'th'} option`

    slot.append(number, box)
    optionKeysRow.appendChild(slot)
    return box
})

function readOptionKeys(): string[] {
    return optionKeyBoxes.map((box) => box.value)
}

const answerKeyWarning = document.getElementById('answer-key-warning') as HTMLElement
const bgStatsPlayer = document.getElementById('bgstats-player') as HTMLInputElement
const bgStatsLocation = document.getElementById('bgstats-location') as HTMLInputElement
const marvelCdbDeckIds = document.getElementById('marvelcdb-deck-ids') as HTMLInputElement
const marvelCdbSync = document.getElementById('marvelcdb-sync') as HTMLButtonElement
const marvelCdbStatus = document.getElementById('marvelcdb-status') as HTMLElement
const marvelCdbDecks = document.getElementById('marvelcdb-decks') as HTMLTableElement
const marvelCdbDecksBody = document.getElementById('marvelcdb-decks-body') as HTMLElement
const marvelCdbDecksTools = document.getElementById('marvelcdb-decks-tools') as HTMLElement
const marvelCdbDecksSearch = document.getElementById('marvelcdb-decks-search') as HTMLInputElement
const marvelCdbDecksState = document.getElementById('marvelcdb-decks-state') as HTMLSelectElement
const marvelCdbDecksCount = document.getElementById('marvelcdb-decks-count') as HTMLElement
const marvelCdbDecksSortButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('.synced-decks-sort'))
const marvelCdbDecksPanel = document.getElementById('marvelcdb-decks-panel') as HTMLElement

type SyncedDeck = {
    id: string;
    name: string;
    hero: string;
    // Both added later: state written by an older build has neither, and the
    // table falls back to a decklist link, which is what a bare ID resolves
    // to first anyway.
    kind?: string;
    url?: string;
};

type MarvelCdbSyncResult = {
    ok: boolean;
    synced: SyncedDeck[];
    errors: Array<{id: string; error: string}>;
    // Decks that synced but name cards this installation cannot play.
    // Older sync state predates this field.
    warnings?: Array<{id: string; name: string; cards: string[]}>;
    synced_at: string;
};

type MarvelCdbSyncStatus = {
    deck_ids: string[];
    last_sync: string;
    last_result: MarvelCdbSyncResult|null;
    // The decks actually on disk, named from the deck files rather than from
    // whatever the last sync happened to touch. Older builds do not send it.
    decks?: SyncedDeck[];
};

function updateAnimationTime() {
    const value = Number(animationTime.value)
    animationTimeValue.value = `${value.toFixed(1)} s`
    UserSettings.setAnimationTime(value)
}

/** A MarvelCDB deck/decklist page, which is what the box accepts besides an ID. */
const DECK_URL = /marvelcdb\.com\/(deck|decklist)\/view\/(\d+)/i

/**
 * What the box names, ready to send.
 *
 * A link is as good as an ID here because the server accepts both: rejecting
 * links in the browser only meant a pasted URL failed in the one place a
 * person is most likely to paste one.
 */
function parseDeckIds(value: string): string[] {
    const deckIds: string[] = []
    for( const part of value.split(',') ) {
        const reference = part.trim()
        if( !reference ) {
            continue
        }
        const link = DECK_URL.exec(reference)
        const normalized = link
            ? reference
            : /^\d+$/.test(reference)
                ? reference.replace(/^0+(?=\d)/, '')
                : ''
        if( !normalized ) {
            throw new Error(`Invalid deck ID or link: ${reference}`)
        }
        if( !deckIds.includes(normalized) ) {
            deckIds.push(normalized)
        }
    }
    return deckIds
}

/**
 * The box is for adding, so an empty one is not an error.
 *
 * Sync with nothing typed refreshes everything already in the table; sync with
 * a deck named adds that one. Neither takes anything away -- the table below
 * is where a deck is removed, and it says so.
 */
function updateMarvelCdbControls(showHint=true): string[] {
    const value = marvelCdbDeckIds.value.trim()
    try {
        const deckIds = parseDeckIds(value)
        marvelCdbSync.disabled = false
        if( showHint ) {
            marvelCdbStatus.textContent = deckIds.length === 0
                ? 'Sync refreshes every deck below. Add one by entering its ID or link.'
                : `${deckIds.length} deck${deckIds.length === 1 ? '' : 's'} to add.`
        }
        return deckIds
    } catch( error ) {
        marvelCdbSync.disabled = true
        marvelCdbStatus.textContent = error instanceof Error ? error.message : String(error)
        return []
    }
}

function describeLastSync(syncedAt: string): string {
    if( !syncedAt ) {
        return 'Decks have not been synchronized yet.'
    }
    const at = new Date(syncedAt)
    if( Number.isNaN(at.getTime()) ) {
        return 'Decks were synchronized.'
    }
    return `Last synchronized ${at.toLocaleString()}.`
}

/** The MarvelCDB page for a deck, from what the sync recorded or from its ID. */
function deckPageUrl(deck: SyncedDeck): string {
    if( deck.url ) {
        return deck.url
    }
    // `decklist` first, matching the order the sync itself probes a bare ID in.
    const kind = deck.kind === 'deck' ? 'deck' : 'decklist'
    return `https://marvelcdb.com/${kind}/view/${encodeURIComponent(deck.id)}`
}

function cell(text: string, className?: string): HTMLTableCellElement {
    const td = document.createElement('td')
    td.textContent = text
    if( className ) {
        td.className = className
    }
    return td
}

/** One row of the table, worked out once and drawn as often as the filters change. */
type DeckRowState = 'ok'|'warned'|'failed'|'pending'
type DeckRow = {
    id: string;
    name: string;
    hero: string;
    deck: SyncedDeck;
    state: DeckRowState;
    stateText: string;
}
type DeckSortKey = 'name'|'hero'|'id'|'state'

let deckRows: DeckRow[] = []
let deckSort: {key: DeckSortKey; dir: 1|-1} = {key: 'name', dir: 1}

/**
 * What is actually being kept in step, one row per deck.
 *
 * Driven by the configured IDs rather than by the last result, so a deck that
 * failed to sync still has a row saying so -- a deck silently missing from a
 * list of successes is the case this table exists to make visible. IDs with
 * no record yet show as pending until the first sync reports on them.
 */
function renderSyncedDecks(status: MarvelCdbSyncStatus): void {
    const result = status.last_result
    const byId = new Map<string, SyncedDeck>()
    // The decks on disk first, so every one of them is named whether or not
    // the last sync touched it, then the last result over the top of them
    // because that is the fresher account of the ones it did touch.
    for( const deck of status.decks ?? [] ) {
        byId.set(deck.id, deck)
    }
    for( const deck of result?.synced ?? [] ) {
        byId.set(deck.id, deck)
    }
    const errorsById = new Map<string, string>()
    for( const error of result?.errors ?? [] ) {
        errorsById.set(error.id, error.error)
    }
    const warningsById = new Map<string, number>()
    for( const warning of result?.warnings ?? [] ) {
        warningsById.set(warning.id, warning.cards.length)
    }

    deckRows = []
    for( const ref of status.deck_ids ?? [] ) {
        // A reference is `123`, `deck/123` or `decklist/123`.
        const parts = String(ref).split('/')
        const id = parts[parts.length - 1] ?? ''
        const kind = parts.length > 1 ? parts[0] : undefined
        const deck = byId.get(id) ?? {id, name: '', hero: '', kind}
        const error = errorsById.get(id)
        const missingCards = warningsById.get(id)

        let state: DeckRowState
        let stateText: string
        if( error ) {
            state = 'failed'
            stateText = error
        } else if( byId.has(id) ) {
            // "Synced" says this deck is here and being kept in step, which is
            // true of every deck on disk -- not only the ones the last press
            // of the button happened to cover.
            state = missingCards ? 'warned' : 'ok'
            stateText = missingCards
                ? `Synced · ${missingCards} card${missingCards === 1 ? '' : 's'} not implemented`
                : 'Synced'
        } else {
            state = 'pending'
            stateText = 'Not synced yet'
        }
        deckRows.push({id, name: deck.name, hero: deck.hero, deck, state, stateText})
    }

    drawSyncedDecks()
}

/** Attention first when sorting by state: what failed, then what is short of cards. */
const STATE_RANK: Record<DeckRowState, number> = {failed: 0, warned: 1, pending: 2, ok: 3}

function compareDeckRows(a: DeckRow, b: DeckRow): number {
    let order = 0
    switch( deckSort.key ) {
        case 'name':
            order = (a.name || '\uffff').localeCompare(b.name || '\uffff')
            break
        case 'hero':
            order = (a.hero || '\uffff').localeCompare(b.hero || '\uffff')
            break
        case 'id':
            order = Number(a.id) - Number(b.id)
            if( Number.isNaN(order) ) {
                order = a.id.localeCompare(b.id)
            }
            break
        case 'state':
            order = STATE_RANK[a.state] - STATE_RANK[b.state]
            break
    }
    if( order === 0 ) {
        order = a.name.localeCompare(b.name) || a.id.localeCompare(b.id)
    }
    return order * deckSort.dir
}

/**
 * The rows that pass the search and the state filter, in the chosen order,
 * with the count saying how many that is out of how many there are.
 */
function drawSyncedDecks(): void {
    const total = deckRows.length
    const query = marvelCdbDecksSearch.value.trim().toLowerCase()
    const wantedState = marvelCdbDecksState.value
    const shown = deckRows
        .filter(row => wantedState === 'all' || row.state === wantedState)
        .filter(row => !query
            || row.name.toLowerCase().includes(query)
            || row.hero.toLowerCase().includes(query)
            || row.id.includes(query))
        .sort(compareDeckRows)

    const rows: HTMLTableRowElement[] = shown.map(({id, deck, state, stateText}) => {
        const row = document.createElement('tr')
        row.append(
            cell(deck.name || '—', 'synced-deck-name'),
            cell(deck.hero || '—'),
        )

        const idCell = document.createElement('td')
        const link = document.createElement('a')
        link.href = deckPageUrl(deck)
        link.textContent = id
        link.target = '_blank'
        link.rel = 'noopener noreferrer'
        link.className = 'synced-deck-link'
        idCell.appendChild(link)
        row.appendChild(idCell)

        row.appendChild(cell(stateText, `synced-deck-${state}`))

        const actions = document.createElement('td')
        const remove = document.createElement('button')
        remove.type = 'button'
        remove.className = 'synced-deck-remove'
        remove.textContent = 'Remove'
        remove.title = `Stop syncing ${deck.name || id} and delete this copy`
        remove.addEventListener('click', () => void forgetDeck(id, deck.name))
        actions.appendChild(remove)
        row.appendChild(actions)
        return row
    })

    if( total > 0 && rows.length === 0 ) {
        const row = document.createElement('tr')
        row.className = 'synced-decks-empty'
        const td = cell('No decks match.')
        td.colSpan = 5
        row.appendChild(td)
        rows.push(row)
    }

    marvelCdbDecksBody.replaceChildren(...rows)
    const decks = `${total} deck${total === 1 ? '' : 's'}`
    marvelCdbDecksCount.textContent = shown.length === total ? decks : `${shown.length} of ${decks}`
    for( const button of marvelCdbDecksSortButtons ) {
        const th = button.closest('th')
        if( button.dataset.sort === deckSort.key ) {
            th?.setAttribute('aria-sort', deckSort.dir === 1 ? 'ascending' : 'descending')
        } else {
            th?.removeAttribute('aria-sort')
        }
    }
    // The panel carries the border and the scroll, so it goes with the table
    // rather than standing there as an empty box.
    marvelCdbDecksTools.hidden = total === 0
    marvelCdbDecks.hidden = total === 0
    marvelCdbDecksPanel.hidden = total === 0
}

marvelCdbDecksSearch.addEventListener('input', drawSyncedDecks)
marvelCdbDecksState.addEventListener('change', drawSyncedDecks)
for( const button of marvelCdbDecksSortButtons ) {
    button.addEventListener('click', () => {
        const key = button.dataset.sort as DeckSortKey
        // The same heading again turns the order round; a new one starts ascending.
        deckSort = key === deckSort.key ? {key, dir: deckSort.dir === 1 ? -1 : 1} : {key, dir: 1}
        drawSyncedDecks()
    })
}

/**
 * Take a deck out of the table, which is the only thing that takes one out.
 *
 * Confirmed first: this deletes the local copy as well as stopping the
 * refresh, so the deck leaves Quick Game too. It is still on MarvelCDB, and
 * entering its ID again brings it back.
 */
async function forgetDeck(deckId: string, name: string): Promise<void> {
    const label = name ? `${name} (${deckId})` : deckId
    if( !window.confirm(`Stop syncing ${label} and delete this installation's copy?`) ) {
        return
    }
    marvelCdbStatus.textContent = `Removing ${label}…`
    try {
        const response = await fetch('/forget_marvelcdb_decks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({deck_ids: [deckId]}),
        })
        const result = await response.json() as {removed?: unknown[]; error?: string}
        if( !response.ok ) {
            throw new Error(result.error || `${response.status} ${response.statusText}`)
        }
        await loadMarvelCdbStatus()
        marvelCdbStatus.textContent = `Removed ${label}.`
    } catch( error ) {
        console.error(error)
        marvelCdbStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not remove the deck.'
    }
}

async function loadMarvelCdbStatus(): Promise<void> {
    try {
        const response = await fetch('/marvelcdb_sync_status')
        if( !response.ok ) {
            throw new Error(`${response.status} ${response.statusText}`)
        }
        const status = await response.json() as MarvelCdbSyncStatus
        // The box is deliberately left empty. Filling it with the whole roster
        // was what made it look like the list of decks -- and then editing it
        // looked like editing that list, which is how ninety-odd decks came to
        // be dropped by typing one id over them.
        updateMarvelCdbControls(false)
        marvelCdbStatus.textContent = status.last_result
            ? describeLastSync(status.last_sync)
            : 'Decks have not been synchronized yet.'
        renderSyncedDecks(status)
    } catch( error ) {
        console.error(error)
        updateMarvelCdbControls(false)
        marvelCdbStatus.textContent = 'Could not load MarvelCDB synchronization status.'
    }
}

animationTime.value = UserSettings.getAnimationTime().toString()
animationTimeValue.value = `${ANIMATION_TIME_DEFAULT.toFixed(1)} s`
updateAnimationTime()

autoSaveReplays.checked = UserSettings.getAutoSaveReplays()
skipSingleTargetConfirm.checked = UserSettings.getSkipSingleTargetConfirm()
confirmKey.value = UserSettings.getConfirmKey()
denyKey.value = UserSettings.getDenyKey()
undoKey.value = UserSettings.getUndoKey()
updateKeyWarning()
bgStatsPlayer.value = UserSettings.getBgStatsPlayerName()
bgStatsLocation.value = UserSettings.getBgStatsLocation()
// The deck box starts empty and is not remembered. It names decks to add;
// what is already here is the table, which the server keeps.
updateMarvelCdbControls()

animationTime.addEventListener('input', updateAnimationTime)
autoSaveReplays.addEventListener('change', () => {
    UserSettings.setAutoSaveReplays(autoSaveReplays.checked)
})
skipSingleTargetConfirm.addEventListener('change', () => {
    UserSettings.setSkipSingleTargetConfirm(skipSingleTargetConfirm.checked)
})

/**
 * The two answer keys, captured by pressing them rather than typed.
 *
 * A key you press is the key you get: typing "esc" into a box and hoping is
 * how a setting ends up bound to the letter e.
 */
function keyLabel(key: string): string {
    return key === ' ' ? 'Space' : key
}

/** Say what a chosen key already does at the table, without refusing it. */
function updateKeyWarning(): void {
    const notes: string[] = []
    // Undo is tested first at the table, so it is the one that happens.
    const pairs = [
        [confirmKey, denyKey, 'OK and cancel', 'cancel'],
        [confirmKey, undoKey, 'OK and undo', 'undo'],
        [denyKey, undoKey, 'Cancel and undo', 'undo'],
    ] as const
    for( const [a, b, both, wins] of pairs ) {
        if( a.value && a.value === b.value ) {
            notes.push(`${both} are the same key, so only ${wins} will happen.`)
        }
    }
    for( const [box, role] of [[confirmKey, 'confirm'], [denyKey, 'cancel'],
                               [undoKey, 'undo']] as const ) {
        const existing = whatKeyDoes(box.value)
        if( existing ) {
            // A key you chose wins outright, so say that rather than implying
            // the table will try to do both.
            notes.push(
                `${keyLabel(box.value)} already does "${existing}" at the table. `
                + `Your key wins, so it will ${role} instead.`)
        }
    }
    answerKeyWarning.textContent = notes.join(' ')
    updateOptionKeyWarning()
}

/**
 * What an option key will lose to, if anything.
 *
 * The table tests the three chosen answers before the options, and takes the
 * first position holding a key when two hold the same one, so both of these
 * are about which of two things a press will do.
 */
function updateOptionKeyWarning(): void {
    const notes: string[] = []
    const chosen = [[confirmKey, 'OK'], [denyKey, 'cancel'], [undoKey, 'undo']] as const
    const keys = readOptionKeys()

    keys.forEach((key, at) => {
        if( !key ) {
            return
        }
        const answer = chosen.find(([box]) => box.value && box.value === key)
        if( answer ) {
            notes.push(
                `${keyLabel(key)} is your ${answer[1]} key, so option ${at + 1} `
                + 'will not answer to it.')
        }
        const earlier = keys.findIndex((other) => other === key)
        if( earlier < at ) {
            notes.push(
                `${keyLabel(key)} is on options ${earlier + 1} and ${at + 1}, `
                + `so it will take option ${earlier + 1}.`)
        }
    })

    optionKeyWarning.textContent = notes.join(' ')
}

function bindKeyBox(box: HTMLInputElement, save: (key: string) => void): void {
    box.addEventListener('focus', () => {
        box.classList.add('listening')
        box.value = ''
    })
    box.addEventListener('blur', () => {
        box.classList.remove('listening')
        // Left empty on purpose is a real answer: it turns the second key off.
        save(box.value)
        updateKeyWarning()
    })
    box.addEventListener('keydown', (event) => {
        event.preventDefault()
        if( event.key === 'Tab' ) {
            box.blur()
            return
        }
        // A modifier on its own is somebody still reaching for the key.
        if( ['Shift', 'Control', 'Alt', 'Meta'].includes(event.key) ) {
            return
        }
        box.value = event.key
        save(event.key)
        updateKeyWarning()
        box.blur()
    })
}

bindKeyBox(confirmKey, (key) => UserSettings.setConfirmKey(key))
bindKeyBox(denyKey, (key) => UserSettings.setDenyKey(key))
bindKeyBox(undoKey, (key) => UserSettings.setUndoKey(key))

function paintOptionKeys(keys: readonly string[]): void {
    optionKeyBoxes.forEach((box, at) => {box.value = keys[at] ?? ''})
    updateKeyWarning()
}

paintOptionKeys(UserSettings.getOptionKeys())
for( const box of optionKeyBoxes ) {
    bindKeyBox(box, () => UserSettings.setOptionKeys(readOptionKeys()))
}
optionKeysReset.addEventListener('click', () => {
    UserSettings.setOptionKeys(DEFAULT_OPTION_KEYS)
    paintOptionKeys(DEFAULT_OPTION_KEYS)
})

for( const button of document.querySelectorAll<HTMLButtonElement>('.key-clear') ) {
    button.addEventListener('click', () => {
        const box = document.getElementById(button.dataset.clears!) as HTMLInputElement
        box.value = ''
        if( box === confirmKey ) {
            UserSettings.setConfirmKey('')
        } else if( box === undoKey ) {
            UserSettings.setUndoKey('')
        } else {
            UserSettings.setDenyKey('')
        }
        updateKeyWarning()
    })
}
bgStatsPlayer.addEventListener('input', () => {
    UserSettings.setBgStatsPlayerName(bgStatsPlayer.value)
})
bgStatsLocation.addEventListener('input', () => {
    UserSettings.setBgStatsLocation(bgStatsLocation.value)
})
marvelCdbDeckIds.addEventListener('input', () => updateMarvelCdbControls())
marvelCdbSync.addEventListener('click', async () => {
    const deckIds = updateMarvelCdbControls(false)
    if( marvelCdbSync.disabled ) {
        return
    }

    marvelCdbSync.disabled = true
    marvelCdbSync.setAttribute('aria-busy', 'true')
    marvelCdbStatus.textContent = deckIds.length
        ? 'Adding from MarvelCDB…'
        : 'Refreshing decks from MarvelCDB…'
    try {
        const response = await fetch('/sync_marvelcdb_decks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({deck_ids: deckIds}),
        })
        const result = await response.json() as MarvelCdbSyncResult & {error?: string}
        if( !response.ok ) {
            throw new Error(result.error || `${response.status} ${response.statusText}`)
        }
        // The box has done its job; the table is the list from here.
        marvelCdbDeckIds.value = ''
        // Re-read the roster rather than drawing the table from what was just
        // typed: what was typed is one deck, and the table is all of them.
        await loadMarvelCdbStatus()
        marvelCdbStatus.textContent = describeLastSync(result.synced_at)
    } catch( error ) {
        console.error(error)
        marvelCdbStatus.textContent = error instanceof Error
            ? error.message
            : 'MarvelCDB synchronization failed.'
    } finally {
        marvelCdbSync.removeAttribute('aria-busy')
        updateMarvelCdbControls(false)
    }
})

void loadMarvelCdbStatus()
