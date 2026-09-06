// What a card does, inferred from its printed text and stats.
//
// Nothing in the data says what a card is for, so it has to be read off the
// rules text. That text is written in a tightly controlled vocabulary -- the
// game's own keyword tags are in it, italicised -- which makes a rule-based
// reading workable where free English would not be.
//
// This is deliberately about what a card *does*, not what it is *for in a
// given deck*. A 3-cost ally is a chump blocker in one deck and a swarm
// payload in another and the text reads identically, so a profile can rank
// plausible replacements but cannot know a deck's plan.

export type CardPaperLike = {
    card_id?: string;
    type?: string;
    name?: string;
    desc?: Record<string, string>;
    traits?: string[];
    text?: string;
    pack?: string;
};

/** The jobs a player card can do. Costs paid to use a card are not jobs. */
export type CardFunction =
    | 'damage'
    | 'thwart'
    | 'defence'
    | 'heal'
    | 'draw'
    | 'ready'
    | 'resource'
    | 'tutor'
    | 'status'
    | 'cancel'
    | 'buff'
    | 'body'
    | 'ramp'
    | 'recursion';

export type CardTiming =
    | 'action'
    | 'response'
    | 'interrupt'
    | 'resource'
    | 'special'
    | 'passive';

export type CardProfile = {
    /** Job to magnitude. 0 means the card does this without a printed number. */
    functions: Map<CardFunction, number>;
    timings: Set<CardTiming>;
    /** True where the ability is restricted to one form. */
    heroOnly: boolean;
    alterEgoOnly: boolean;
    cost: number | null;
    /** Printed resource icons, e.g. "YY". */
    resources: string;
    type: string;
    traits: string[];
    /** Deckbuilding class: an aspect, `Basic`, or `Hero` for signature cards. */
    aspect: string;
    unique: boolean;
};

const ASPECTS: ReadonlySet<string> = new Set([
    'Aggression', 'Justice', 'Leadership', 'Protection',
]);

/** Markup is stripped before matching, but the keyword tags are kept first. */
function stripMarkup(text: string): string {
    return text.replace(/<[^>]+>/g, '');
}

/**
 * Record that a card does `key`, at `amount` when a number was printed.
 *
 * Only ever called where there is evidence. Writing a zero unconditionally is
 * what made an early version report every card as doing everything.
 */
function raise(functions: Map<CardFunction, number>, key: CardFunction, amount = 0): void {
    // Several clauses can name the same job; the biggest number is the one
    // that characterises the card.
    functions.set(key, Math.max(functions.get(key) ?? 0, amount));
}

/** Record `key` only if the pattern matches, using its number when it has one. */
function raiseIfMatch(
    functions: Map<CardFunction, number>,
    key: CardFunction,
    text: string,
    pattern: RegExp,
): void {
    const match = text.match(pattern);
    if (!match) {
        return;
    }
    const value = match[1] === undefined ? NaN : Number(match[1]);
    raise(functions, key, Number.isFinite(value) ? value : 0);
}

function readTimings(text: string): {
    timings: Set<CardTiming>;
    heroOnly: boolean;
    alterEgoOnly: boolean;
} {
    const timings = new Set<CardTiming>();
    let heroOnly = false;
    let alterEgoOnly = false;

    // Bold tags carry the timing, sometimes with a trailing colon inside them.
    for (const match of text.matchAll(/<b>([^<]+)<\/b>/g)) {
        const label = match[1].replace(/:\s*$/, '').trim().toLowerCase();
        if (label.includes('hero ')) {
            heroOnly = true;
        }
        if (label.includes('alter-ego')) {
            alterEgoOnly = true;
        }
        if (label.includes('resource')) {
            timings.add('resource');
        } else if (label.includes('interrupt')) {
            timings.add('interrupt');
        } else if (label.includes('response')) {
            timings.add('response');
        } else if (label.includes('action')) {
            timings.add('action');
        } else if (label === 'special') {
            timings.add('special');
        }
    }
    if (timings.size === 0) {
        timings.add('passive');
    }
    return {timings, heroOnly, alterEgoOnly};
}

export function profileCard(paper: CardPaperLike): CardProfile {
    const raw = String(paper.text ?? '');
    const desc = paper.desc ?? {};
    const plain = stripMarkup(raw);
    const lower = plain.toLowerCase();
    const functions = new Map<CardFunction, number>();

    // The italicised keyword tags are the game's own statement of what an
    // ability is for, so they are trusted even when no number is printed.
    if (/\(attack(\/\w+)?\)/i.test(raw)) {
        raise(functions, 'damage', 0);
    }
    if (/\(thwart(\/\w+)?\)/i.test(raw) || /\(\w+\/thwart\)/i.test(raw)) {
        raise(functions, 'thwart', 0);
    }
    if (/\(defense(\/\w+)?\)/i.test(raw) || /\(\w+\/defense\)/i.test(raw)) {
        raise(functions, 'defence', 0);
    }

    raiseIfMatch(functions, 'damage', lower, /deals? (\d+) damage/);
    raiseIfMatch(functions, 'thwart', lower, /remove (\d+) threat/);
    raiseIfMatch(functions, 'heal', lower, /heals? (\d+) damage/);
    raiseIfMatch(functions, 'draw', lower, /draws? (\d+) card/);

    if (/\bdeal damage\b/.test(lower)) {
        raise(functions, 'damage', 0);
    }
    if (/\bremove .* threat\b/.test(lower)) {
        raise(functions, 'thwart', 0);
    }
    if (/\bheal\b/.test(lower)) {
        raise(functions, 'heal', 0);
    }
    if (/\bdraws? (?:a|another|\d+) cards?\b|\bdraws? cards\b/.test(lower)) {
        raise(functions, 'draw', 0);
    }
    if (/\bready\b/.test(lower)) {
        raise(functions, 'ready', 0);
    }
    if (/\b(stun|confuse|tough)\b/.test(lower)) {
        raise(functions, 'status', 0);
    }
    if (/\b(cancel|prevent)\b/.test(lower)) {
        raise(functions, 'cancel', 0);
    }
    if (/search your (deck|collection)|look at the top|reveal the top/.test(lower)) {
        raise(functions, 'tutor', 0);
    }
    if (/\bgets? \+\d|\+\d+ (atk|thw|def)|increase\b/.test(lower)) {
        raise(functions, 'buff', 0);
    }
    if (/\bdefend\b/.test(lower)) {
        raise(functions, 'defence', 0);
    }
    // Paying less for what comes next is a job in its own right, and a common
    // one: Helicarrier and its like do nothing else.
    if (/reduce the (?:resource )?cost|costs? \d+ less/.test(lower)) {
        raise(functions, 'ramp');
    }
    // Bringing something back beats finding a fresh copy, so it is worth
    // telling apart from a deck search.
    if (/from (?:your|any player's) discard pile|put .{0,24}into play/.test(lower)) {
        raise(functions, 'recursion');
    }
    // Taking a hit that was aimed elsewhere is defence, however it is worded.
    if (/take it as damage instead|would be placed .{0,30}instead/.test(lower)) {
        raise(functions, 'defence');
    }

    const {timings, heroOnly, alterEgoOnly} = readTimings(raw);
    if (timings.has('resource') || paper.type === 'Resource') {
        raise(functions, 'resource', 0);
    }

    // An ally's printed stats are a job in themselves: it can be thrown in
    // front of an attack and it can attack or thwart on its own.
    const attack = Number(String(desc.ATK ?? '').replace(/\D/g, ''));
    const thwart = Number(String(desc.THW ?? '').replace(/\D/g, ''));
    const health = Number(String(desc.HP ?? '').replace(/\D/g, ''));
    if (paper.type === 'Ally') {
        if (Number.isFinite(health) && health > 0) {
            raise(functions, 'body', health);
        }
        if (Number.isFinite(attack) && attack > 0) {
            raise(functions, 'damage', attack);
        }
        if (Number.isFinite(thwart) && thwart > 0) {
            raise(functions, 'thwart', thwart);
        }
    }

    const costText = String(desc.Cost ?? '').trim();
    const cost = /^\d+$/.test(costText) ? Number(costText) : null;

    return {
        functions,
        timings,
        heroOnly,
        alterEgoOnly,
        cost,
        resources: String(desc.RES ?? ''),
        type: String(paper.type ?? ''),
        traits: paper.traits ?? [],
        aspect: String(desc.Class ?? ''),
        unique: String(paper.name ?? '').trim().startsWith('*'),
    };
}

/** Aspect classes a card belongs to, e.g. `Hero;Justice` gives both. */
export function aspectsOf(profile: CardProfile): string[] {
    return profile.aspect.split(';').map((part) => part.trim()).filter(Boolean);
}

/** Whether this card may appear in a deck's aspect/basic portion at all. */
export function isSubstitutable(profile: CardProfile): boolean {
    const classes = aspectsOf(profile);
    // `Hero` marks a hero's own signature cards, which belong to that hero and
    // can never stand in for anything. No class at all means the card is not a
    // player card -- an identity, or an encounter card.
    if (classes.includes('Hero') || classes.length === 0) {
        return false;
    }
    // `Campaign` cards are dealt by a campaign rather than built into a deck.
    // Several are `Campaign;Basic`, so the Basic half must not smuggle them in.
    if (classes.includes('Campaign')) {
        return false;
    }
    return classes.some((name) => ASPECTS.has(name) || name === 'Basic');
}

const FUNCTION_LABELS: Record<CardFunction, string> = {
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
    ramp: 'cost reduction',
    recursion: 'recursion',
};

/** A short human reason, for showing next to a suggestion. */
export function describeProfile(profile: CardProfile): string {
    const jobs = [...profile.functions.entries()]
        .sort((left, right) => right[1] - left[1])
        .slice(0, 3)
        .map(([key, amount]) => amount > 0
            ? `${FUNCTION_LABELS[key]} ${amount}`
            : FUNCTION_LABELS[key]);
    const cost = profile.cost === null ? '' : `${profile.cost}-cost `;
    const aspect = aspectsOf(profile).filter((name) => name !== 'Hero')[0] ?? '';
    const head = `${cost}${aspect} ${profile.type}`.replace(/\s+/g, ' ').trim();
    return jobs.length ? `${head} — ${jobs.join(', ')}` : head;
}
