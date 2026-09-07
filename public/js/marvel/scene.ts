import { Lib } from './lib.js'
import { Setting } from "./settings.js";
import { HoverCard } from './hover.js';

// The stage is a fixed-size coordinate space that gets scaled to fit the
// window, so a display wider than 16:9 was letterboxed and the surplus width
// was unusable. The stage now widens to the window's aspect instead.
//
// It only ever grows: never going below the design width means every existing
// position keeps working, and a narrow or tall window behaves exactly as
// before. The cap stops an extreme aspect ratio from stranding the decks
// against far edges with an ocean of felt in between.
//
// "The design width" is whatever the stylesheet asks for at this moment, not a
// number known here. Three are in use -- 1920 as the base, 1600 for a desktop
// at 3:2 or wider, 1440 for a 4:3 tablet -- and each comes with its own set of
// furniture coordinates that place the schemes some 20 to 40 units from the
// right edge of *that* stage. Assuming 1920 stretched the two narrower stages
// while leaving their furniture where it was, so the schemes ended up hundreds
// of units inboard, and the centre column -- which centres on the real width --
// slid right into them.
const MAX_SCENE_WIDTH = 3440;

/**
 * The stage width the stylesheet asks for, media queries included.
 *
 * Read with our own override lifted, since that override is the answer to this
 * question from the last resize and would otherwise be mistaken for the
 * stylesheet's.
 */
function designSceneWidth(): number {
    const root = document.documentElement;
    const override = root.style.getPropertyValue('--scene-width');
    if (override) {
        root.style.removeProperty('--scene-width');
    }
    const design = parseFloat(getComputedStyle(root).getPropertyValue('--scene-width'));
    if (override) {
        root.style.setProperty('--scene-width', override);
    }
    return design;
}

// Decks and scheme rows pinned to the right-hand edge. Their stylesheet --x is
// an absolute stage coordinate that assumes the design width, so the distance
// from the right edge is captured once and reapplied whenever the stage grows.
const RIGHT_ANCHORED_SELECTOR = [
    '#victory-display',
    '#removed-pool',
    '#area-removed',
    '#nemesis-pool',
    '#area-advanced',
    '#area-schemes-main',
    '#area-schemes-side',
].join(', ');

/** Fired when the stage width changes and card positions need recomputing. */
export const SCENE_WIDTH_CHANGED = 'scene-width-changed';

/** Drop our overrides so the stylesheet decides these positions again. */
function clearRightAnchors(): void {
    for (const element of document.querySelectorAll<HTMLElement>(RIGHT_ANCHORED_SELECTOR)) {
        element.style.removeProperty('--x');
    }
}

/**
 * Set the stage width and re-pin the right-hand furniture.
 *
 * The offsets are measured fresh every time rather than cached once. The Cerebro
 * theme moves these decks inward under a `min-aspect-ratio: 3 / 2` media query,
 * so a cached offset would go stale the moment the window crossed that
 * breakpoint -- and because the override is inline, it would win over the media
 * query permanently. Clearing first also means the design width needs no
 * overrides at all: the stylesheet is already right there.
 *
 * `designWidth` is the stage those furniture coordinates were written for, and
 * is what each one's distance from the right edge is measured against.
 *
 * Returns whether anything changed, so a relayout is only requested when needed.
 */
function applySceneWidth(width: number, designWidth: number): boolean {
    const root = document.documentElement;
    const current = parseFloat(getComputedStyle(root).getPropertyValue('--scene-width'));
    if (current === width) {
        return false;
    }

    clearRightAnchors();
    if (width === designWidth) {
        // Removed rather than set to the same number, so that crossing a media
        // query later changes the stage: an inline value equal to today's
        // design width would outlive the breakpoint that made it right.
        root.style.removeProperty('--scene-width');
        return true;
    }
    root.style.setProperty('--scene-width', width.toString());

    // getComputedStyle after the clear reflects the stylesheet, media queries
    // included, so this reads the positions the theme actually wants right now.
    for (const element of document.querySelectorAll<HTMLElement>(RIGHT_ANCHORED_SELECTOR)) {
        const x = Number(getComputedStyle(element).getPropertyValue('--x'));
        if (Number.isFinite(x)) {
            element.style.setProperty('--x', (width - (designWidth - x)).toString());
        }
    }
    return true;
}

export class Scene {
    static scale: number = 0

    static init() {
        // Adjust scale on DOMContentLoaded
        document.addEventListener('DOMContentLoaded', () => {
            adjustSceneScale()
        });

        // Adjust scale on resize
        window.onresize = () => {
            adjustSceneScale();
        }

        // import { HoverCard } from "./hover.js";
        if( Setting.scene_3d ) {
            Lib.loader.loadCSS("./css./marvel./scene-3d.css")
            document.body.classList.add('scene-3d')
        }
    }
}

// Function to convert scene position to window position
export function convertScenePosToWindowPos(sceneX: number, sceneY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    // Get the current scale of the scene
    const scale = Scene.scale; // Assuming Scene.scale holds the current scale value

    // Calculate the window position
    const windowX = (sceneX * scale) + rect.left; // Adjusted X position in window coordinates
    const windowY = (sceneY * scale) + rect.top;  // Adjusted Y position in window coordinates

    return { x: windowX, y: windowY };
}

// Function to get mouse position relative to the scene
export function getMousePositionInScene(windowX: number, windowY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    // Calculate the mouse position relative to the scene
    const mouseX = windowX - rect.left; // Mouse X relative to the scene
    const mouseY = windowY - rect.top;  // Mouse Y relative to the scene

    // Adjust for scaling
    const scale = Scene.scale; // Extract the scale value
    const sceneX = mouseX / scale; // Adjusted X position
    const sceneY = mouseY / scale; // Adjusted Y position

    return { x: sceneX, y: sceneY };
}

export function adjustSceneScale() {
    const camera = document.getElementById('camera')!;
    const rootStyles = getComputedStyle(document.documentElement); // Get the root element's styles

    const sceneHeight = parseFloat(rootStyles.getPropertyValue('--scene-height'));

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Match the stage to the window's aspect so a wide display fills out
    // instead of being letterboxed, within the bounds set above.
    const designWidth = designSceneWidth();
    const widthForAspect = Math.round(sceneHeight * (viewportWidth / viewportHeight));
    const sceneWidth = Math.min(
        MAX_SCENE_WIDTH, Math.max(designWidth, widthForAspect));
    const widthChanged = applySceneWidth(sceneWidth, designWidth);

    // Calculate scale factors
    const scaleX = viewportWidth / sceneWidth;
    const scaleY = viewportHeight / sceneHeight;
    Scene.scale = Math.min(scaleX, scaleY); // Use the smaller scale to fit within the viewport

    // Apply the scale transformation
    camera.style.transform = `scale(${Scene.scale})`;
    if( Setting.scene_3d ) {
        document.getElementById('scene')!.style.transform = `scale(1) rotateX(20deg)`;
    }
    camera.style.display = "unset";

    // Center the scene in the viewport
    camera.style.left = `${(viewportWidth - (sceneWidth * Scene.scale)) / 2}px`;
    camera.style.top = `${(viewportHeight - (sceneHeight * Scene.scale)) / 2}px`;

    // Set the new value for the CSS variable
    // Must use `parseInt`
    const x = parseInt(rootStyles.getPropertyValue('--font-size'));
    document.documentElement.style.setProperty('--font-size-out', `${x * Scene.scale}px`);

    HoverCard.updateRect()

    // Card positions were computed against the old stage width, so they need
    // recomputing. Announced as an event rather than calling the layout code
    // directly: scene.ts and the layout module would otherwise import each
    // other, and this file is already in a cycle with hover.js.
    if (widthChanged) {
        window.dispatchEvent(new CustomEvent(SCENE_WIDTH_CHANGED));
    }
}

