// Suggesting cards you own that could stand in for one you do not.
//
// Ranked on what a card does rather than on aspect, cost and type matching.
// Those three usually do line up between a card and its replacement, but they
// are a consequence of a good match rather than the thing being matched: a
// 2-cost Justice event that removes threat and a 2-cost Justice event that
// cancels a treachery share every one of them and swap badly.
//
// What this cannot know is what a card is for in *your* deck. A profile says a
// card deals damage; it cannot say the copy in your list was there to trigger
// something else. Suggestions are a starting point for a person, not a verdict.

import {
    CardFunction,
    CardPaperLike,
    CardProfile,
    aspectsOf,
    describeProfile,
    isSubstitutable,
    profileCard,
} from './card_profile.js';

export type SubstitutionCandidate = {
    paper: CardPaperLike;
    profile: CardProfile;
    /** 0..1, dominated by how closely the jobs line up. */
    score: number;
    /** Short phrases explaining the match, best first. */
    reasons: string[];
};

export type SubstitutionRequest = {
    target: CardPaperLike;
    /** Every card in the game, already flattened out of cards.json. */
    pool: readonly CardPaperLike[];
    /** Product keys the player owns. */
    ownedPacks: ReadonlySet<string>;
    /** How many cards of each aspect the deck holds, e.g. {Justice: 15}. */
    deckAspectCounts: ReadonlyMap<string, number>;
    /** Card ids already in the deck, so a suggestion is not one you have. */
    deckCardIds: ReadonlySet<string>;
    limit?: number;
};

// A replacement is chosen for what it does; everything else only breaks ties.
const WEIGHT_FUNCTION = 0.62;
const WEIGHT_COST = 0.14;
const WEIGHT_TYPE = 0.12;
const WEIGHT_RESOURCE = 0.07;
const WEIGHT_TRAIT = 0.05;

/** How well one magnitude stands in for another, 0..1. */
function magnitudeMatch(wanted: number, offered: number): number {
    if (wanted <= 0 || offered <= 0) {
        // One side is unquantified, so the jobs match but the sizes cannot be
        // compared. Neither reward nor punish that.
        return 0.75;
    }
    return Math.min(wanted, offered) / Math.max(wanted, offered);
}

function functionScore(target: CardProfile, candidate: CardProfile): number {
    if (target.functions.size === 0) {
        // Nothing was read off the target, so its jobs cannot drive the match
        // and the remaining signals have to carry it.
        return 0;
    }
    let matched = 0;
    for (const [job, wanted] of target.functions) {
        const offered = candidate.functions.get(job);
        if (offered !== undefined) {
            matched += magnitudeMatch(wanted, offered);
        }
    }
    const covered = matched / target.functions.size;

    // A card that also does three unrelated things is a worse stand-in than one
    // that does the same job and little else.
    const extra = Math.max(0, candidate.functions.size - target.functions.size);
    return covered * (1 - Math.min(extra, 4) * 0.06);
}

function costScore(target: CardProfile, candidate: CardProfile): number {
    if (target.cost === null || candidate.cost === null) {
        return 0.5;
    }
    return Math.max(0, 1 - Math.abs(target.cost - candidate.cost) / 4);
}

function resourceScore(target: CardProfile, candidate: CardProfile): number {
    const wanted = new Set(target.resources.split(''));
    if (wanted.size === 0) {
        return 0.5;
    }
    const shared = candidate.resources.split('').some((icon) => wanted.has(icon));
    return shared ? 1 : 0;
}

function traitScore(target: CardProfile, candidate: CardProfile): number {
    if (target.traits.length === 0) {
        return 0.5;
    }
    const wanted = new Set(target.traits);
    const shared = candidate.traits.filter((trait) => wanted.has(trait)).length;
    return shared / target.traits.length;
}

const ASPECT_NAMES: ReadonlySet<string> = new Set([
    'Aggression', 'Justice', 'Leadership', 'Protection',
]);

/** An aspect present in such small numbers that it is a deliberate include. */
const SPLASH_LIMIT = 3;

function aspectsOnly(profile: CardProfile): string[] {
    return aspectsOf(profile).filter((name) => ASPECT_NAMES.has(name));
}

/**
 * The classes a replacement for this card may belong to.
 *
 * Like for like, or Basic. Swapping a card for one of its own aspect leaves
 * the deck's aspect counts exactly as they were, so the result stays legal
 * whatever the hero's deckbuilding rule is -- which matters because several
 * heroes have their own. Cable, Maria Hill and Gamora can each carry a few
 * off-aspect cards, Spider-Woman gets two full aspects, Adam Warlock a slice
 * of all four; taking the union of everything in the deck would have offered
 * any Aggression card as a replacement for a Leadership one in a Cable deck,
 * where the single off-aspect slot is already spent.
 *
 * A Basic card is the one case with no aspect to preserve, so it may be
 * replaced by Basic or by the deck's main aspect, which is always allowed.
 */
function legalAspectsFor(
    target: CardProfile,
    deckAspectCounts: ReadonlyMap<string, number>,
): Set<string> {
    const own = aspectsOnly(target);
    if (own.length > 0) {
        return new Set([...own, 'Basic']);
    }
    let primary = '';
    let best = 0;
    for (const [aspect, count] of deckAspectCounts) {
        if (count > best) {
            primary = aspect;
            best = count;
        }
    }
    return new Set(primary ? ['Basic', primary] : ['Basic']);
}

function isLegalInDeck(profile: CardProfile, allowed: ReadonlySet<string>): boolean {
    return aspectsOf(profile).some((name) => allowed.has(name));
}

/**
 * Whether the card being replaced is an off-aspect include.
 *
 * Those are chosen for a specific reason rather than as filler, so a
 * like-for-like suggestion is far less likely to be what you want. Detected
 * from the deck rather than from a list of heroes, so it holds for any hero.
 */
export function isSplashInclude(
    target: CardPaperLike,
    deckAspectCounts: ReadonlyMap<string, number>,
): boolean {
    const own = aspectsOnly(profileCard(target));
    if (own.length === 0) {
        return false;
    }
    const total = [...deckAspectCounts.values()].reduce((sum, n) => sum + n, 0);
    return own.every((aspect) => {
        const count = deckAspectCounts.get(aspect) ?? 0;
        // Small in absolute terms and a minority of the deck: one or two
        // Aggression cards among fifteen Leadership ones.
        return count <= SPLASH_LIMIT && count * 4 < total;
    });
}

const FUNCTION_WORDS: Record<CardFunction, string> = {
    damage: 'damage',
    thwart: 'thwart',
    defence: 'defence',
    heal: 'healing',
    draw: 'card draw',
    ready: 'readying',
    resource: 'resources',
    tutor: 'deck search',
    status: 'status effects',
    cancel: 'cancellation',
    buff: 'stat boost',
    body: 'a body',
    recursion: 'recursion',
    ramp: 'cost reduction',
};

function explain(target: CardProfile, candidate: CardProfile): string[] {
    const reasons: string[] = [];

    const shared = [...target.functions.keys()]
        .filter((job) => candidate.functions.has(job))
        .map((job) => {
            const amount = candidate.functions.get(job) ?? 0;
            // The size matters as much as the job: swapping damage 3 for
            // damage 1 is a different decision from swapping it for damage 3.
            return amount > 0 ? `${FUNCTION_WORDS[job]} ${amount}` : FUNCTION_WORDS[job];
        });
    if (shared.length) {
        reasons.push(`also does ${shared.join(' and ')}`);
    }

    const missed = [...target.functions.keys()]
        .filter((job) => !candidate.functions.has(job))
        .map((job) => FUNCTION_WORDS[job]);
    if (missed.length) {
        reasons.push(`but not ${missed.join(' or ')}`);
    }

    if (target.cost !== null && candidate.cost !== null) {
        const difference = candidate.cost - target.cost;
        if (difference === 0) {
            reasons.push('same cost');
        } else {
            reasons.push(`${Math.abs(difference)} ${difference > 0 ? 'more' : 'less'} to play`);
        }
    }
    if (candidate.type !== target.type) {
        reasons.push(`${candidate.type.toLowerCase()} rather than ${target.type.toLowerCase()}`);
    }
    return reasons;
}

export function suggestSubstitutes(request: SubstitutionRequest): SubstitutionCandidate[] {
    const {target, pool, ownedPacks, deckAspectCounts, deckCardIds} = request;
    const limit = request.limit ?? 6;
    const targetProfile = profileCard(target);
    const allowedAspects = legalAspectsFor(targetProfile, deckAspectCounts);

    const scored: SubstitutionCandidate[] = [];
    for (const paper of pool) {
        if (!paper.card_id || paper.card_id === target.card_id) {
            continue;
        }
        // Suggesting something already in the list is not a substitution.
        if (deckCardIds.has(paper.card_id)) {
            continue;
        }
        if (!paper.pack || !ownedPacks.has(paper.pack)) {
            continue;
        }
        const profile = profileCard(paper);
        if (!isSubstitutable(profile) || !isLegalInDeck(profile, allowedAspects)) {
            continue;
        }

        const score =
            WEIGHT_FUNCTION * functionScore(targetProfile, profile)
            + WEIGHT_COST * costScore(targetProfile, profile)
            + WEIGHT_TYPE * (profile.type === targetProfile.type ? 1 : 0.35)
            + WEIGHT_RESOURCE * resourceScore(targetProfile, profile)
            + WEIGHT_TRAIT * traitScore(targetProfile, profile);

        scored.push({paper, profile, score, reasons: explain(targetProfile, profile)});
    }

    scored.sort((left, right) =>
        right.score - left.score
        || String(left.paper.name).localeCompare(String(right.paper.name)));

    // A card reprinted in more than one product appears once per printing, and
    // offering the same card twice wastes a slot. Sorted first, so the copy
    // kept is the best-scoring one -- which is also the one from a product the
    // player owns, since unowned printings never got this far.
    const seen = new Set<string>();
    const unique: SubstitutionCandidate[] = [];
    for (const candidate of scored) {
        const name = String(candidate.paper.name ?? '').replace(/^\*\s*/, '');
        if (seen.has(name)) {
            continue;
        }
        seen.add(name);
        unique.push(candidate);
        if (unique.length >= limit) {
            break;
        }
    }
    return unique;
}

/** How many cards of each aspect a deck holds, from the cards in it. */
export function deckAspectCountsOf(
    papers: readonly CardPaperLike[],
): Map<string, number> {
    const counts = new Map<string, number>();
    for (const paper of papers) {
        for (const name of aspectsOnly(profileCard(paper))) {
            counts.set(name, (counts.get(name) ?? 0) + 1);
        }
    }
    return counts;
}

export {describeProfile};
