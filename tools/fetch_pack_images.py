"""Download card images for packs the usual image servers do not carry yet.

The app already fetches card art at runtime from Cerebro and MarvelCDB (see
`image_servers` in launch.json), and that covers everything up to Fear No Evil.
It does not cover the Jessica Jones or Luke Cage packs: Cerebro has no 61xxx or
62xxx images at all, and MarvelCDB has only the two identity cards. A pack can
be played without art -- the app draws a readable text face instead -- but a
table of text faces is a worse table.

Hall of Heroes publishes scans of the cards in its pack reviews. They are named
after the card rather than numbered, so the mapping below is by hand, and every
entry was read off the scan itself: the card number is printed in the bottom
right corner of each one, and that is what was matched, not the filename.

The images are written to ./assets/pics/, which the image cache checks before
any server (see engine/file/cache.py) and which .gitignore keeps out of the
repository -- this fetches card art, it does not vendor it. On the NAS, that
folder is a bind mount, so run this once against the deployment and the images
stay put across rebuilds:

    python tools/fetch_pack_images.py                # every pack listed here
    python tools/fetch_pack_images.py --pack jj
    python tools/fetch_pack_images.py --list         # print, download nothing
    python tools/fetch_pack_images.py --force        # re-fetch what is there

Cards whose entry is missing simply keep their text face, and a reprint with no
entry falls back to the art of the printing it links to.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICS = os.path.join(ROOT, 'assets', 'pics')

HOH = 'https://hallofheroeslcg.com/wp-content/uploads/'

# card_id -> image url. Verified against the card number printed on each scan.
JESSICA_JONES: Dict[str, str] = {
    # The hero set.
    '61001a': HOH + '2026/05/mc61_cards_jessica-jones_hero.png',
    '61001b': HOH + '2026/05/mc61_cards_jessica-jones_alter-ego.png',
    '61002':  HOH + '2026/05/mc61_cards_alias-investigations.png',
    '61003':  HOH + '2026/05/mc61_cards_luke-cage.png',
    '61004':  HOH + '2026/05/mc61_cards_big-mistake.png',
    '61005':  HOH + '2026/05/mc61_cards_breakthrough.png',
    '61006':  HOH + '2026/05/mc61_cards_snooping-around.png',
    '61007':  HOH + '2026/05/mc61_cards_piecing-it-all-together-1.png',
    '61008':  HOH + '2026/05/mc61_cards_calling-in-favors.png',
    '61009':  HOH + '2026/05/mc61_cards_4k-digital-camcorder.png',
    '61010':  HOH + '2026/05/mc61_cards_circumstantial-evidence.png',
    '61011':  HOH + '2026/05/mc61_cards_leather-jacket.png',
    '61012':  HOH + '2026/06/1.jpg',
    '61013':  HOH + '2026/06/2.jpg',
    '61014':  HOH + '2026/05/mc61_cards_stakeout.png',

    # Justice.
    '61015':  HOH + '2026/05/mc61_cards_captain-marvel.png',
    '61016':  HOH + '2026/07/jessica-jones-hero-pack-17-2.webp',
    '61017':  HOH + '2026/05/mc61_cards_squirrel-girl.png',
    '61019':  HOH + '2026/05/mc61_cards_strategy-session.png',
    '61020':  HOH + '2026/05/mc61_cards_run-them-to-ground.png',
    '61021':  HOH + '2026/07/jessica-jones-hero-pack-22.png',
    '61023':  HOH + '2026/05/mc61_cards_grapnel-launcher.png',
    '61024':  HOH + '2026/05/mc61_cards_entrapment.png',
    '61036':  '',  # Innate Perception -- not published anywhere yet.

    # Basic.
    '61025':  HOH + '2026/07/jessica-jones-hero-pack-26-2.webp',
    '61026':  HOH + '2026/05/mc61_cards_joys-of-life.png',
    '61027':  HOH + '2026/05/mc61_cards_unbreakable-bond.png',
    '61028':  HOH + '2026/07/jessica-jones-hero-pack-29-4.png',
    '61029':  HOH + '2026/05/mc61_cards_defend-our-city.png',

    # The nemesis set and the obligation.
    '61030':  HOH + '2026/07/jessica-jones-hero-pack-31-1.webp',
    '61031':  HOH + '2026/06/grafik.webp',
    '61032':  HOH + '2026/06/grafik-1.webp',
    '61033a': HOH + '2026/06/grafik-2.webp',
    '61033b': HOH + '2026/06/grafik-4.webp',
    '61033c': HOH + '2026/06/grafik-3.webp',

    # The remaining aspects.
    '61034':  HOH + '2026/06/23.jpg',
    '61035':  HOH + '2026/07/jessica-jones-hero-pack-38.webp',
    '61037':  HOH + '2026/06/45.jpg',
    '61038':  '',  # Echo -- not published anywhere yet.
    '61039':  HOH + '2026/07/jessica-jones-hero-pack-42.png',
    '61040':  HOH + '2026/07/jessica-jones-hero-pack-43.webp',
}

# The numbers in the "luke-cage-hero-pack-N" filenames are the site's own
# upload sequence, not card numbers: each one is the card numbered N-1. That
# was read off the scans rather than assumed, and every entry below was matched
# to the number printed in its bottom right corner.
LUKE_CAGE: Dict[str, str] = {
    # The hero set.
    '62001a': HOH + '2026/06/mc62_luke-cage_hero.png',
    '62001b': HOH + '2026/06/mc62_luke-cage_alter-ego.png',
    '62002':  HOH + '2026/06/mc62_luke-cage_jessica-jones.png',
    '62003':  HOH + '2026/06/1-1.jpg',
    '62004':  HOH + '2026/06/mc62_luke-cage_knuckle-sandwich.png',
    '62005':  HOH + '2026/06/mc62_luke-cage_stand-with-me.png',
    '62006':  HOH + '2026/06/mc62_luke-cage_sweet-christmas.png',
    '62007':  HOH + '2026/06/2.png',
    '62008':  HOH + '2026/06/mc62_luke-cage_burstein_process.png',
    '62009':  '',  # Cruisin' for a Bruisin' -- not published anywhere yet.
    '62010':  HOH + '2026/06/mc62_luke-cage_metal-bracers.png',
    '62011':  HOH + '2026/06/mc62_luke-cage_power-man.png',

    # Leadership.
    '62012':  HOH + '2026/06/mc62_luke-cage_iron-fist.png',
    '62013':  HOH + '2026/06/mc62_luke-cage_misty-knight.png',
    '62014':  HOH + '2026/07/luke-cage-hero-pack-15.webp',
    '62015':  HOH + '2026/06/mc62_luke-cage_take-a-stand.png',
    '62016':  HOH + '2026/07/img_1483.webp',
    '62018':  HOH + '2026/06/mc62_luke-cage_defensive-formation.png',
    '62019':  HOH + '2026/06/mc62_luke-cage_righteous-purpose.png',

    # Basic.
    '62020':  HOH + '2026/07/luke-cage-hero-pack-21.webp',
    '62021':  HOH + '2026/07/luke-cage-hero-pack-22.webp',
    '62022':  HOH + '2026/06/mc62_luke-cage_dynamic-duo.png',
    '62023':  HOH + '2026/06/mc62_luke-cage_power-man_iron-fist.png',
    '62024':  HOH + '2026/06/mc62_luke-cage_unbreakable-bond.png',

    # The obligation and the nemesis set.
    '62028':  HOH + '2026/07/luke-cage-hero-pack-29.webp',
    '62029':  HOH + '2026/07/luke-cage-hero-pack-30.webp',
    '62030':  HOH + '2026/07/luke-cage-hero-pack-31.png',
    '62031':  HOH + '2026/07/luke-cage-hero-pack-32.webp',
    '62032':  HOH + '2026/07/luke-cage-hero-pack-33.webp',
    '62033':  HOH + '2026/07/luke-cage-hero-pack-34.webp',

    # The remaining aspects.
    '62034':  HOH + '2026/07/luke-cage-hero-pack-35.webp',
    '62035':  HOH + '2026/07/luke-cage-hero-pack-36.webp',
    '62036':  HOH + '2026/07/luke-cage-37.webp',
    '62037':  HOH + '2026/07/luke-cage-hero-pack-38-1.webp',
}

PACKS: Dict[str, Dict[str, str]] = {
    'jj': JESSICA_JONES,
    'luke_cage': LUKE_CAGE,
}

# The cache tries these in order, so the extension has to be one it knows.
KNOWN_SUFFIXES = ('.webp', '.jpg', '.png')

USER_AGENT = 'marvel-lcg card image fetcher'


def existing(card_id: str) -> str:
    for suffix in KNOWN_SUFFIXES:
        path = os.path.join(PICS, card_id + suffix)
        if os.path.exists(path):
            return path
    return ''


def suffix_of(url: str) -> str:
    lowered = url.lower()
    for suffix in KNOWN_SUFFIXES:
        if lowered.endswith(suffix):
            return suffix
    if lowered.endswith('.jpeg'):
        return '.jpg'
    return ''


def download(url: str, path: str) -> int:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    # Written whole rather than streamed: a half-written image is a card that
    # renders as a broken box until somebody notices and deletes it by hand.
    with open(path, 'wb') as file:
        file.write(data)
    return len(data)


def run(packs: List[str], force: bool, list_only: bool) -> int:
    wanted: List[Tuple[str, str]] = []
    for pack in packs:
        for card_id, url in sorted(PACKS[pack].items()):
            wanted.append((card_id, url))

    if not list_only:
        os.makedirs(PICS, exist_ok=True)

    fetched = 0
    skipped = 0
    absent = 0
    failed = 0

    for card_id, url in wanted:
        if not url:
            absent += 1
            print('  no image  %-8s (not published)' % card_id)
            continue

        suffix = suffix_of(url)
        if not suffix:
            failed += 1
            print('  BAD URL   %-8s %s' % (card_id, url))
            continue

        here = existing(card_id)
        if here and not force:
            skipped += 1
            print('  have      %-8s %s' % (card_id, os.path.basename(here)))
            continue

        path = os.path.join(PICS, card_id + suffix)
        if list_only:
            print('  would get %-8s %s' % (card_id, url))
            continue

        try:
            size = download(url, path)
        except (urllib.error.URLError, OSError) as error:
            failed += 1
            print('  FAILED    %-8s %s: %s' % (card_id, url, error))
            continue

        fetched += 1
        print('  got       %-8s %6d bytes  %s' % (card_id, size, os.path.basename(path)))
        # Unhurried on purpose. This is somebody's blog, not a CDN, and the
        # whole run is a few dozen files.
        time.sleep(0.25)

    print('%d fetched, %d already present, %d not published, %d failed'
          % (fetched, skipped, absent, failed))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--pack', action='append', choices=sorted(PACKS),
                        help='only this pack; repeatable. Default: all of them.')
    parser.add_argument('--force', action='store_true',
                        help='download again even where an image is already present')
    parser.add_argument('--list', action='store_true', dest='list_only',
                        help='print what would be fetched and stop')
    args = parser.parse_args()

    return run(args.pack or sorted(PACKS), args.force, args.list_only)


if __name__ == '__main__':
    sys.exit(main())
