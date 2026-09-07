// Reading traits, and what a deck does with them.
//
// A trait is written two different ways in the card data. The `traits` array
// shouts them -- `X-MEN`, `S.H.I.E.L.D`, `AERIAL` -- while the rules text tags
// them in title case and with its own punctuation: `[[X-Men]]`,
// `[[S.H.I.E.L.D.]]`, `[[Aerial]]`. Matching the two literally finds almost
// nothing, and does so silently: an early pass here reported S.H.I.E.L.D. as
// paid off by eighteen cards and carried by none, which is not a thing that
// can be true. Every comparison therefore goes through `normaliseTrait`.
//
// The `[[...]]` markup is not only for traits -- `[[consequential]]` and
// `[[boost]]` are keywords wearing the same brackets -- so a tag counts only
// once it matches a trait some card actually carries.

import { CardPaperLike } from './card_profile.js';

/** A trait reduced to a form both spellings agree on. */
export function normaliseTrait(trait: string): string {
    return trait.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

const TAG_PATTERN = /\[\[([^\]]+)\]\]/g;

/**
 * Every trait any card carries, normalised.
 *
 * Built from the card pool rather than written down here, so a trait arriving
 * with a new product needs no change: the pool is the whole of cards.json.
 */
export function buildTraitVocabulary(
    pool: readonly CardPaperLike[],
): Map<string, string> {
    const vocabulary = new Map<string, string>();
    for (const paper of pool) {
        for (const trait of paper.traits ?? []) {
            const key = normaliseTrait(trait);
            if (key && !vocabulary.has(key)) {
                vocabulary.set(key, trait);
            }
        }
    }
    return vocabulary;
}

/** The traits a card carries, normalised. */
export function traitsOf(paper: CardPaperLike): Set<string> {
    const traits = new Set<string>();
    for (const trait of paper.traits ?? []) {
        const key = normaliseTrait(trait);
        if (key) {
            traits.add(key);
        }
    }
    return traits;
}

/**
 * The traits a card's text pays off, normalised.
 *
 * "Pays off" is deliberately loose: searching for an X-Men support, buffing
 * X-Men allies and costing less while you control an X-Men card all count.
 * They differ in kind but agree on the thing that matters here -- the deck is
 * better off holding cards with that trait.
 */
export function payoffTraitsOf(
    paper: CardPaperLike,
    vocabulary: ReadonlyMap<string, string>,
): Set<string> {
    const paid = new Set<string>();
    const text = String(paper.text ?? '');
    for (const match of text.matchAll(TAG_PATTERN)) {
        const key = normaliseTrait(match[1]);
        if (vocabulary.has(key)) {
            paid.add(key);
        }
    }
    return paid;
}

const IDENTITY_GATE =
    /only if your identity has the \[\[([^\]]+)\]\] trait/i;

/**
 * The trait an identity must carry for this card to be playable, if any.
 *
 * Sixty-eight player cards carry this clause, and it is not a preference: a
 * hero without the trait can never play the card. Across a 96-deck collection,
 * 84% of hero-and-gated-card pairings are dead, so offering these unfiltered
 * meant most such suggestions were cards that would sit in hand all game.
 */
export function identityGateOf(paper: CardPaperLike): string | null {
    const match = String(paper.text ?? '').match(IDENTITY_GATE);
    return match ? normaliseTrait(match[1]) : null;
}

/** How much a deck wants each trait, by normalised trait. */
export type TraitDemand = ReadonlyMap<string, number>;

/**
 * A trait counts as demanded when the deck both asks for it and can field it.
 *
 * Both halves are needed. Text alone catches cards that name a trait the deck
 * has no way to supply -- an Elite-hating card in a deck holding no Elites --
 * and carriers alone would call any deck with three Aerial allies an Aerial
 * deck, which it is not unless something rewards them.
 */
const MIN_PAYOFFS = 2;
const MIN_CARRIERS = 3;

/**
 * How much of the deck is on each side of a trait's bargain.
 *
 * Rarity across the whole card pool was the first thing tried here and it was
 * backwards: it floored X-Men, Avenger and Guardian -- the traits decks are
 * actually built around -- at the minimum, while lifting whatever happened to
 * be printed rarely. What matters is not how unusual a trait is in the game
 * but how much of *this* deck is committed to it, on both sides at once, so
 * the payoffs and the cards that feed them are multiplied.
 *
 * Payoffs are counted per distinct card, carriers per copy. Three copies of
 * one card are one opinion about what the deck is for, but three chances to
 * draw the payload.
 */
function participation(payoffs: number, carriers: number, deckSize: number): number {
    // Calibrated against a 96-deck collection: the median themed deck lands
    // near 0.7 and the decks whose names say what they are -- "50 Shades of
    // X-Men" at 7.1, an Aerial deck at 5.6 -- run well past 1, so saturating
    // here separates a theme from an overlap without splitting hairs above it.
    return Math.min(1, (payoffs * carriers) / Math.max(1, deckSize));
}

/**
 * Work out which traits this deck is built around.
 *
 * `deckPapers` is the whole constructed deck -- identity and signature cards
 * included, since those are as much a reason to run a trait as anything in the
 * aspect half, and an X-Force identity is often the only reason the theme is
 * there at all.
 */
export function buildTraitDemand(
    deckPapers: readonly CardPaperLike[],
    vocabulary: ReadonlyMap<string, string>,
): Map<string, number> {
    const payoffs = new Map<string, Set<string>>();
    const carriers = new Map<string, number>();
    for (const paper of deckPapers) {
        for (const trait of payoffTraitsOf(paper, vocabulary)) {
            const names = payoffs.get(trait) ?? new Set<string>();
            names.add(String(paper.name ?? paper.card_id ?? ''));
            payoffs.set(trait, names);
        }
        for (const trait of traitsOf(paper)) {
            carriers.set(trait, (carriers.get(trait) ?? 0) + 1);
        }
    }

    const demand = new Map<string, number>();
    for (const [trait, names] of payoffs) {
        const paid = names.size;
        const held = carriers.get(trait) ?? 0;
        if (paid < MIN_PAYOFFS || held < MIN_CARRIERS) {
            continue;
        }
        demand.set(trait, participation(paid, held, deckPapers.length));
    }
    return demand;
}
