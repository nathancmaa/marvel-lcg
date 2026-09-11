// What is wrong with a deck, said out loud rather than enforced.
//
// A deck that breaks a rule still plays here: this is a solo table, the rules
// are yours to bend, and a netdeck built for a card this installation has not
// implemented is a thing you may well want to try anyway. What costs a game is
// not knowing -- in true solo an illegal deck usually announces itself in the
// middle of a turn, by which point the turn is spent.
//
// Everything here is read from the card pool the app already ships. Nothing is
// written down twice: the aspect of a card is its Class field, a copy limit is
// its MaxPerDeck, and an identity gate is parsed from its own text by the same
// code the substitution engine uses.

import { CardPaperLike, profileCard } from './card_profile.js';
import { identityGateOf, normaliseTrait } from './card_traits.js';

export type DeckWarning = {
    /** Grouped so a caller can style or filter them; the text is the message. */
    kind: 'size' | 'aspect' | 'copies' | 'identity' | 'missing';
    text: string;
};

/** The minimum a player deck may be built to. */
const MIN_DECK_SIZE = 40;

/** The copy limit for a card that does not print its own. */
const DEFAULT_MAX_COPIES = 3;

/** Classes that are not an aspect choice. */
const NOT_AN_ASPECT: ReadonlySet<string> = new Set(['Basic', 'Hero', 'Campaign']);

let poolPromise: Promise<Map<string, CardPaperLike>> | null = null;

/**
 * Every card, by id.
 *
 * The pool is about 2.4 MB, so this is called when a deck is actually being
 * looked at rather than when a page loads, and cached for the life of the page.
 */
export function loadCardPapers(): Promise<Map<string, CardPaperLike>> {
    if (!poolPromise) {
        poolPromise = (async () => {
            const response = await fetch('/get_cards_json?');
            if (!response.ok) {
                throw new Error(`get_cards_json returned ${response.status}`);
            }
            const packs = await response.json() as Record<string, unknown>;
            const papers = new Map<string, CardPaperLike>();
            for (const cards of Object.values(packs)) {
                if (!Array.isArray(cards)) {
                    continue;
                }
                for (const card of cards as CardPaperLike[]) {
                    if (card?.card_id) {
                        papers.set(card.card_id, card);
                    }
                }
            }
            return papers;
        })().catch((error) => {
            // Cleared so a later attempt retries rather than reusing a failure.
            poolPromise = null;
            throw error;
        });
    }
    return poolPromise;
}

/**
 * The ids in one deck entry.
 *
 * An entry names every face of a card at once -- "46001a,46001b" is Iceman and
 * Bobby Drake. Reading only the first is how an X-Men deck was told its
 * MUTANT-gated cards were unplayable: the trait is on the alter-ego, which is
 * the face that was being dropped.
 */
function faceIdsOf(value: string): string[] {
    return String(value ?? '').split(',').map((id) => id.trim()).filter(Boolean);
}

function plural(count: number, one: string, many: string): string {
    return count === 1 ? one : many;
}

/** Names, listed readably and cut off before they become a wall. */
function listNames(names: readonly string[], limit = 4): string {
    const shown = names.slice(0, limit);
    const rest = names.length - shown.length;
    const joined = shown.length > 1
        ? `${shown.slice(0, -1).join(', ')} and ${shown[shown.length - 1]}`
        : shown[0] ?? '';
    return rest > 0 ? `${joined}, and ${rest} more` : joined;
}

export type DeckToCheck = {
    /** Identity card ids, which carry the hero's traits. */
    hero: readonly string[];
    /** The hero's own signature cards, which count toward the deck minimum. */
    hero_deck: readonly string[];
    /** Player deck card ids, one entry per copy. */
    player_deck: readonly string[];
};

/**
 * Everything questionable about a deck, in the order it is worth knowing.
 *
 * Returns an empty list for a deck with nothing to say about it, so a caller
 * can treat "no warnings" as "say nothing" rather than "say it is legal" --
 * this does not check every rule, and claiming a clean bill would be a bigger
 * promise than it can keep.
 */
export function checkDeck(
    deck: DeckToCheck,
    papers: ReadonlyMap<string, CardPaperLike>,
): DeckWarning[] {
    const warnings: DeckWarning[] = [];

    // -- what the hero is, from the identity cards themselves ---------------
    // Every face: the hero form and the alter-ego carry different traits, and
    // a card gated on either is playable.
    const identityTraits = new Set<string>();
    for (const value of deck.hero) {
        for (const id of faceIdsOf(value)) {
            for (const trait of papers.get(id)?.traits ?? []) {
                identityTraits.add(normaliseTrait(trait));
            }
        }
    }

    // -- resolve the player deck -------------------------------------------
    const resolved: CardPaperLike[] = [];
    const missing: string[] = [];
    for (const value of deck.player_deck) {
        const id = faceIdsOf(value)[0] ?? '';
        const paper = papers.get(id);
        if (paper) {
            resolved.push(paper);
        } else if (id) {
            missing.push(id);
        }
    }

    // -- size ---------------------------------------------------------------
    // The minimum counts the hero's signature cards as well as the aspect and
    // basic ones: a starter deck is 15 and 25, which is legal at exactly 40.
    const size = deck.hero_deck.length + deck.player_deck.length;
    if (size < MIN_DECK_SIZE) {
        warnings.push({
            kind: 'size',
            text: `${size} cards, counting signature cards.`
                + ` ${MIN_DECK_SIZE} is the minimum.`,
        });
    }

    // -- aspects ------------------------------------------------------------
    const aspectCounts = new Map<string, number>();
    for (const paper of resolved) {
        for (const name of String(profileCard(paper).aspect ?? '').split(';')) {
            const aspect = name.trim();
            if (aspect && !NOT_AN_ASPECT.has(aspect)) {
                aspectCounts.set(aspect, (aspectCounts.get(aspect) ?? 0) + 1);
            }
        }
    }
    if (aspectCounts.size > 1) {
        const parts = [...aspectCounts.entries()]
            .sort((left, right) => right[1] - left[1])
            .map(([aspect, count]) => `${aspect} ${count}`);
        warnings.push({
            kind: 'aspect',
            // Not stated as an error: Spider-Woman builds with two aspects and
            // Adam Warlock with all four, and their identities say so rather
            // than the deck doing anything wrong.
            text: `Cards from ${aspectCounts.size} aspects — ${parts.join(', ')}.`
                + ' Most heroes may use only one, though some are built for more.',
        });
    }

    // -- copies -------------------------------------------------------------
    const copies = new Map<string, {count: number; limit: number; name: string}>();
    for (const paper of resolved) {
        const name = String(paper.name ?? '').replace(/^\*\s*/, '').trim();
        if (!name) {
            continue;
        }
        const printed = Number(paper.desc?.MaxPerDeck);
        const limit = Number.isFinite(printed) ? printed : DEFAULT_MAX_COPIES;
        const current = copies.get(name);
        if (current) {
            current.count += 1;
        } else {
            copies.set(name, {count: 1, limit, name});
        }
    }
    const overLimit = [...copies.values()].filter((entry) => entry.count > entry.limit);
    for (const entry of overLimit) {
        warnings.push({
            kind: 'copies',
            text: `${entry.count} copies of ${entry.name}, which allows ${entry.limit}.`,
        });
    }

    // -- identity gates -----------------------------------------------------
    // Only checked when the identity resolved: with no traits to compare
    // against, every gated card would look wrong.
    if (identityTraits.size > 0) {
        const gated = new Map<string, string>();
        for (const paper of resolved) {
            const gate = identityGateOf(paper);
            if (gate && !identityTraits.has(gate)) {
                gated.set(String(paper.name ?? '').replace(/^\*\s*/, '').trim(), gate);
            }
        }
        if (gated.size > 0) {
            const names = [...gated.keys()];
            warnings.push({
                kind: 'identity',
                text: `${listNames(names)} ${plural(names.length, 'needs', 'need')}`
                    + ' an identity trait this hero does not have, so'
                    + ` ${plural(names.length, 'it', 'they')} cannot be played.`,
            });
        }
    }

    // -- cards this installation does not have ------------------------------
    if (missing.length > 0) {
        warnings.push({
            kind: 'missing',
            text: `${missing.length} ${plural(missing.length, 'card is', 'cards are')}`
                + ' not implemented here and will be missing from the deck.',
        });
    }

    return warnings;
}
