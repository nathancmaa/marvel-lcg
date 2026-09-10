"""Draw the Cerebro favicon.

The fork inherited its icon from upstream, which said nothing about this
build. This draws the one it uses now: the helmet, in the gold and blue the
rest of the interface is already in.

Here as a script rather than a binary somebody once made, so the mark can be
adjusted without redrawing it from memory in an image editor -- the same
reason tools/build_universal_decks.py exists.

    python tools/make_favicon.py            # writes public/favicon.ico
    python tools/make_favicon.py --png x.png # a large flat copy, to look at

Everything is drawn at 8x and scaled down, which is what gives the curves
clean edges: PIL's own drawing has no anti-aliasing.
"""

from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ICO = os.path.join(ROOT, 'public', 'favicon.ico')

# The interface's own colours: the deep blue-black every page sits on, the
# gold that marks your own decks, and the blue used for what is selected.
GROUND = (16, 28, 40, 255)
EDGE = (58, 85, 104, 255)
GOLD = (232, 189, 98, 255)
GOLD_DIM = (176, 137, 63, 255)
BLUE = (120, 210, 255, 255)

SCALE = 8
SIZE = 256
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def draw_icon() -> Image.Image:
    """The helmet, drawn large so it can be scaled down smoothly."""
    box = SIZE * SCALE
    image = Image.new('RGBA', (box, box), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def s(value: float) -> float:
        """A coordinate in the 256 design, in drawing units."""
        return value * SCALE

    # The ground: a rounded square rather than a circle, so the mark still has
    # corners at 16 pixels where a circle would read as a smudge.
    draw.rounded_rectangle(
        [s(6), s(6), s(250), s(250)],
        radius=s(56), fill=GROUND, outline=EDGE, width=int(s(4)),
    )

    # A C, not a helmet.
    #
    # The helmet was drawn twice and read as a hard hat once and a car the
    # other time: a dome with two discs beside it needs more pixels than a
    # browser tab gives it. A letter survives 16 pixels, and the fork is
    # called Cerebro, so the letter is the mark.
    outer, inner = s(88), s(54)
    centre = s(128)
    draw.ellipse(
        [centre - outer, centre - outer, centre + outer, centre + outer],
        fill=GOLD,
    )
    draw.ellipse(
        [centre - inner, centre - inner, centre + inner, centre + inner],
        fill=GROUND,
    )
    # The opening, cut to the right and slightly narrow, so the ring still
    # reads as a ring at small sizes rather than a broken circle.
    draw.pieslice(
        [centre - outer * 1.1, centre - outer * 1.1,
         centre + outer * 1.1, centre + outer * 1.1],
        start=-34, end=34, fill=GROUND,
    )
    # The blue that runs through the rest of the interface, on the lower
    # terminal, which is what stops it reading as a plain letter in a circle.
    draw.ellipse(
        [centre + s(30), centre + s(24), centre + s(78), centre + s(66)],
        fill=BLUE,
    )

    return image.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=OUTPUT_ICO)
    parser.add_argument('--png', help='also write a large copy here, to look at')
    args = parser.parse_args()

    icon = draw_icon()
    if args.png:
        icon.save(args.png)
        print(f'wrote {args.png}')

    # Every size in one file: Windows shortcuts and some browsers reach for
    # the large ones, tabs for the 16.
    icon.save(args.out, format='ICO', sizes=ICO_SIZES)
    print(f'wrote {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
