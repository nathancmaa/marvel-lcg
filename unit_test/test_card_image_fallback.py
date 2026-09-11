"""Art for packs the image servers have not published yet.

Fan sites put scans of a new pack up months before Cerebro and MarvelCDB do.
The map in data/card_images.json is where those live; the point of these tests
is that it is only ever a stand-in -- a server always wins when it has the card,
and anything served from the map keeps being offered back to the servers until
one of them does.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from engine.lib.image_creator import ImageCreator
from engine.lib.version import Ver
from engine.file.cache import (
    CACHE_FOLDER,
    IMAGE_FALLBACK_FILE,
    IMAGE_FOLDERS,
    IMAGE_SERVERS,
    TEXTURE_FOLDER,
    Cache,
)


ROOT = Path(__file__).resolve().parents[1]

CEREBRO = (
    "https://cerebrodatastorage.blob.core.windows.net/"
    "cerebro-cards/official/{card_id:U}.jpg"
)
STAND_IN = "https://example.test/stand-in.png"


def answer(content: bytes, content_type: str = "image/png") -> Mock:
    response = Mock()
    response.content = content
    response.headers = {"Content-Type": content_type}
    response.raise_for_status.return_value = None
    return response


def refuse() -> requests.exceptions.RequestException:
    return requests.exceptions.HTTPError("404 Not Found")


class CardImageFallbackTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        ImageCreator.Initialize()

    def setUp(self):
        self.original_memory_cache = Cache.cache
        self.original_map = Cache.fallback_images
        Cache.cache = {}
        Cache.fallback_images = None

    def tearDown(self):
        Cache.cache = self.original_memory_cache
        Cache.fallback_images = self.original_map

    def assets(self, stack: ExitStack, fallback: dict | None = None) -> Path:
        """A temporary assets tree, with an optional fallback map in it.

        Everything is asserted inside the stack: the folders go away with it,
        and so does the patched cache location the index is read from.
        """
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        cache_folder = root / "cache"
        cache_folder.mkdir()

        map_path = root / "card_images.json"
        if fallback is not None:
            map_path.write_text(json.dumps({"images": fallback}), encoding="utf-8")

        stack.enter_context(patch.object(IMAGE_FOLDERS, "value", []))
        stack.enter_context(
            patch.object(TEXTURE_FOLDER, "value", str(root / "textures")))
        stack.enter_context(patch.object(CACHE_FOLDER, "value", str(cache_folder)))
        stack.enter_context(patch.object(IMAGE_FALLBACK_FILE, "value", str(map_path)))
        stack.enter_context(patch.object(IMAGE_SERVERS, "value", [CEREBRO]))
        stack.enter_context(patch(
            "engine.file.cache.ImageLib.TryRotateImage", side_effect=lambda data: data))
        return cache_folder

    # -- the shipped map ----------------------------------------------------

    def test_the_shipped_map_is_card_ids_pointing_at_images(self):
        content = json.loads(
            (ROOT / "data/card_images.json").read_text(encoding="utf-8"))
        images = content["images"]
        self.assertGreater(len(images), 0)

        for card_id, url in images.items():
            with self.subTest(card_id=card_id):
                self.assertTrue(Cache.IsCardId(card_id), card_id)
                self.assertTrue(url.startswith("https://"), url)
                self.assertRegex(url, r"\.(png|jpe?g|webp)$")

    def test_a_missing_map_is_not_an_error(self):
        with ExitStack() as stack:
            self.assets(stack, fallback=None)
            self.assertEqual(Cache.GetFallbackImages(), {})

    # -- resolution order ---------------------------------------------------

    def test_a_server_wins_over_the_map(self):
        with ExitStack() as stack:
            cache_folder = self.assets(stack, {"61015": STAND_IN})
            request = stack.enter_context(patch(
                "engine.file.cache.requests.get",
                return_value=answer(b"official scan", "image/jpeg")))

            image = Cache.LoadImage("61015")

            self.assertEqual(image, b"official scan")
            # Only the server was asked; the stand-in never came up.
            self.assertEqual(len(request.call_args_list), 1)
            self.assertIn("cerebro", request.call_args.args[0])
            self.assertEqual(Cache._LoadFallbackIndex(), {})
            self.assertEqual(
                (cache_folder / "61015.jpg").read_bytes(), b"official scan")

    def test_the_map_is_used_when_no_server_has_the_card(self):
        with ExitStack() as stack:
            cache_folder = self.assets(stack, {"61015": STAND_IN})
            stack.enter_context(patch(
                "engine.file.cache.requests.get",
                side_effect=[refuse(), answer(b"a fan scan")]))

            image = Cache.LoadImage("61015")

            self.assertEqual(image, b"a fan scan")
            self.assertEqual(
                (cache_folder / "61015.png").read_bytes(), b"a fan scan")
            # Recorded, so the refresh knows to keep asking for something better.
            self.assertEqual(Cache._LoadFallbackIndex(), {"61015": STAND_IN})

    def test_a_card_in_neither_falls_back_to_a_text_face(self):
        with ExitStack() as stack:
            self.assets(stack, {})
            stack.enter_context(patch(
                "engine.file.cache.requests.get", side_effect=refuse()))

            image = Cache.LoadImage("99999")

            self.assertGreater(len(image), 0)
            self.assertEqual(Cache._LoadFallbackIndex(), {})

    # -- the refresh --------------------------------------------------------

    def test_the_refresh_replaces_a_stand_in_once_a_server_has_it(self):
        with ExitStack() as stack:
            cache_folder = self.assets(stack, {"61015": STAND_IN})

            with patch("engine.file.cache.requests.get",
                       side_effect=[refuse(), answer(b"a fan scan")]):
                Cache.LoadImage("61015")
            self.assertTrue((cache_folder / "61015.png").exists())

            # A while later, the pack reaches Cerebro.
            with patch("engine.file.cache.requests.get",
                       return_value=answer(b"official scan", "image/jpeg")):
                result = Cache.RefreshFallbackImages()

            self.assertEqual(result, {"checked": 1, "upgraded": 1})
            self.assertEqual(
                (cache_folder / "61015.jpg").read_bytes(), b"official scan")
            # The old extension goes, or a folder scan would keep finding it.
            self.assertFalse((cache_folder / "61015.png").exists())
            # And the decoded copy, or this session keeps serving the scan.
            self.assertNotIn("61015", Cache.cache)
            self.assertEqual(Cache._LoadFallbackIndex(), {})

    def test_the_refresh_keeps_asking_while_no_server_has_it(self):
        with ExitStack() as stack:
            self.assets(stack, {"61015": STAND_IN})

            with patch("engine.file.cache.requests.get",
                       side_effect=[refuse(), answer(b"a fan scan")]):
                Cache.LoadImage("61015")

            with patch("engine.file.cache.requests.get", side_effect=refuse()), \
                    patch("engine.file.cache.Log.Warn") as warn:
                result = Cache.RefreshFallbackImages()

            self.assertEqual(result, {"checked": 1, "upgraded": 0})
            self.assertIn("61015", Cache._LoadFallbackIndex())
            # A server that has not published the card is the expected answer,
            # not a fault: 72 cards refusing twice a day is not a log worth
            # having.
            warn.assert_not_called()

    def test_an_empty_index_does_no_work_at_all(self):
        with ExitStack() as stack:
            self.assets(stack, {})
            request = stack.enter_context(
                patch("engine.file.cache.requests.get"))

            result = Cache.RefreshFallbackImages()

            self.assertEqual(result, {"checked": 0, "upgraded": 0})
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
