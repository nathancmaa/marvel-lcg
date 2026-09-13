// Keep the prompt box off the cards it is asking you to choose between.
//
// #prompt-box-container sits at a fixed `top` in the middle of the board,
// which is exactly where minions and allies sit, so a target prompt routinely
// lands on top of a card you are being asked to pick. While locked the box is
// click-through, so the card underneath stays selectable -- you just cannot
// see which one it is.
//
// Only the locked box is moved. Unlocked, the player has dragged it somewhere
// deliberately and setTempPromptText stops re-centring it, so its position is
// theirs to keep.

/** Cards the current effect will accept as a target. */
const TARGET_SELECTOR = '.highlight-targets';

/** The options and the confirm under them, which sit at a fixed height too. */
const OPTION_AREA_ID = 'option-area';

const STEP = 8;    // px between candidate positions
const MARGIN = 6;  // keep clear of the viewport edge
const GAP = 4;     // breathing room around a card

type Rect = {top: number; bottom: number; left: number; right: number};

function intersects(
    left: number, right: number, top: number, bottom: number, other: Rect,
): boolean {
    return left < other.right + GAP
        && right > other.left - GAP
        && top < other.bottom + GAP
        && bottom > other.top - GAP;
}

let watching = false;
/** The prompt box, once its set-up has named it, for calls with no box to hand. */
let promptBox: HTMLElement | null = null;

/** Measure now, from wherever the confirm under the options has just changed. */
export function keepOptionsClearNow(): void {
    if (promptBox) {
        keepOptionsClearOfPrompt(promptBox);
    }
}

/**
 * Measure again whenever the prompt box or the option area changes size.
 *
 * The confirm under the options is enabled -- and so first takes up room --
 * after the prompt's text is set, and the prompt grows with its text after
 * the options are drawn; neither goes through a call of its own. Sizes are
 * what the observer reports, and the transform the measurement sets changes
 * none, so this cannot loop. Installed once, from the prompt box's set-up.
 */
export function keepOptionsClearAsSizesChange(box: HTMLElement): void {
    promptBox = box;
    const area = document.getElementById(OPTION_AREA_ID);
    if (watching || !area || typeof ResizeObserver === 'undefined') {
        return;
    }
    watching = true;
    const observer = new ResizeObserver(() => keepOptionsClearOfPrompt(box));
    observer.observe(box);
    observer.observe(area);
}

/**
 * Keep the options, and the confirm under them, below the prompt box.
 *
 * The box opens at a fixed height and grows downward with its text; the
 * options sit at a fixed height a little lower. A long prompt with a lone,
 * already-chosen option reaches the confirm button, and what the button
 * then covers is the line that says what is being confirmed. The area is
 * pushed down by exactly the overlap, and the stylesheet's own centring is
 * restored once there is none.
 */
export function keepOptionsClearOfPrompt(box: HTMLElement): void {
    const area = document.getElementById(OPTION_AREA_ID);
    if (!area) {
        return;
    }
    area.style.setProperty('--dodge', '0px');
    if (!box.isConnected || box.classList.contains('hide')) {
        return;
    }
    const prompt = box.getBoundingClientRect();
    const options = area.getBoundingClientRect();
    if (prompt.height === 0 || options.height === 0) {
        return;
    }
    const overlap = prompt.bottom + GAP - options.top;
    if (overlap <= 0 || prompt.right <= options.left || prompt.left >= options.right) {
        return;
    }
    area.style.setProperty('--dodge', `${Math.ceil(overlap)}px`);
}

/**
 * Move `box` vertically, if it would otherwise cover a highlighted target.
 *
 * Called after the prompt is rendered, so the box has its final size. Does
 * nothing when there is no conflict, which keeps it still during the long
 * stretches of a turn where nothing is being selected.
 */
export function dodgeHighlightedTargets(box: HTMLElement, lock: HTMLElement): void {
    if (!box.isConnected || box.classList.contains('hide')) {
        return;
    }
    // Unlocked means the player positioned it by hand; leave it alone.
    if (!lock.classList.contains('locked')) {
        return;
    }

    // Measure from the stylesheet position rather than wherever a previous
    // dodge left it -- the default `top` itself moves when option buttons
    // appear, so a cached value would go stale.
    box.style.top = '';
    const rect = box.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
        return;
    }

    const targets: Rect[] = [];
    for (const element of document.querySelectorAll<HTMLElement>(TARGET_SELECTOR)) {
        const target = element.getBoundingClientRect();
        if (target.width > 0 && target.height > 0) {
            targets.push(target);
        }
    }
    if (targets.length === 0) {
        return;
    }

    const hits = (top: number): boolean => targets.some(
        (target) => intersects(rect.left, rect.right, top, top + rect.height, target),
    );

    const naturalTop = rect.top;
    if (!hits(naturalTop)) {
        return;
    }

    const lowest = MARGIN;
    const highest = window.innerHeight - rect.height - MARGIN;
    if (highest < lowest) {
        // The prompt is taller than the viewport; moving it cannot help.
        return;
    }

    // `top` is resolved against the offset parent, but every measurement here
    // is in viewport space, so convert once rather than assuming the two
    // origins coincide.
    const parent = box.offsetParent as HTMLElement | null;
    const originY = parent ? parent.getBoundingClientRect().top : 0;

    // Search outward from the natural position so the box moves as little as
    // possible, preferring up and down equally at each distance.
    for (let delta = STEP; delta < window.innerHeight; delta += STEP) {
        for (const candidate of [naturalTop - delta, naturalTop + delta]) {
            if (candidate < lowest || candidate > highest) {
                continue;
            }
            if (!hits(candidate)) {
                box.style.top = `${candidate - originY}px`;
                return;
            }
        }
    }
    // Every position collides. Leave the stylesheet default rather than
    // parking the prompt somewhere arbitrary.
}
