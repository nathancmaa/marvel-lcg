from core import *
import json
import os
import requests
from engine.lib import ImageCreator, ImageLib
from engine.log import Log
from engine.file import FileManager
from engine.config import ConfigVariables

CATEGORY_NAME = "CACHE"

IMAGE_FOLDERS   = ConfigVariables.Folders('image_folders', ["./assets/pics/"])
TEXTURE_FOLDER  = ConfigVariables.Folder('texture_folder', "./assets/textures/")
CACHE_FOLDER    = ConfigVariables.Folder('cache_folder', "./assets/cache/")
IMAGE_SERVERS   = ConfigVariables.ListStr('image_servers', [])
# Per-card URLs for art no image server carries. Consulted only after every
# server has been asked, so an official scan always wins when one exists.
IMAGE_FALLBACK_FILE = ConfigVariables.File(
    'image_fallback_file',
    './data/card_images.json',
)
BREAK_WHEN_LOAD_ONLINE_IMAGE = ConfigVariables.Bool('break_when_load_online_image', False)

# Which cached images came from the fallback map rather than from a server.
# Only those are worth re-checking later, and the file empties itself as the
# servers catch up.
FALLBACK_INDEX_NAME = ".fallback-sources.json"

STATUS_TEXTURES = frozenset({"tough", "stunned", "confused"})

# Cerebro names these identity sides after their printed A/B faces, while the
# engine and MarvelCDB consistently use "a" for hero and "b" for alter-ego.
# Keep this source-specific: local images and every other image server already
# use the engine's card ids.
CEREBRO_REVERSED_IDENTITY_BASE_IDS = frozenset({
    "16001",  # Groot
    "16029",  # Rocket Raccoon
    "32001",  # Colossus
    "32030",  # Shadowcat
    "33001",  # Cyclops
    "34001",  # Phoenix
    "35001",  # Wolverine
    "36001",  # Storm
    "37001",  # Gambit
    "38001",  # Rogue
})

# Deliberately still says ronin. This is a cache revision, not a name: it
# is part of every cached identity-side filename, so changing it discards
# the whole card image cache and re-downloads it. Bump it when the images
# need to change, not when the fork does.
CEREBRO_SIDE_CACHE_REVISION = "ronin-side-v1"

class Cache:

    cache: Dict[str, bytes] = {}
    link_pic: Dict[str, str] = {}
    fallback_images: Dict[str, str]|None = None

    @staticmethod
    def SetLinkPic(card_id: str, link_to_pic_id: str):
        Cache.link_pic[card_id] = link_to_pic_id

    ################################################################################
    # Art no image server carries yet
    @staticmethod
    def GetFallbackImages() -> Dict[str, str]:
        """card_id -> URL, for cards the image servers do not have.

        Read once and kept. A missing or unreadable file is not an error: it
        only means every card has to come from a server, which is the normal
        case for every pack older than a month or two.
        """
        if Cache.fallback_images is not None:
            return Cache.fallback_images

        Cache.fallback_images = {}
        path = IMAGE_FALLBACK_FILE.value
        if not path or not FileManager.Exists(path):
            return Cache.fallback_images

        try:
            with FileManager.OpenFile(path, read=True) as file:
                content = json.loads(file.Read())
            images = content.get('images', {}) if isinstance(content, dict) else {}
            Cache.fallback_images = {
                str(card_id): str(url)
                for card_id, url in images.items()
                if url
            }
        except (ValueError, OSError) as error:
            Log.Warn(CATEGORY_NAME, f"Could not read {path}: {error}")
        return Cache.fallback_images

    @staticmethod
    def _FallbackIndexPath() -> str:
        return FileManager.JoinPath(CACHE_FOLDER.value, FALLBACK_INDEX_NAME)

    @staticmethod
    def _LoadFallbackIndex() -> Dict[str, str]:
        path = Cache._FallbackIndexPath()
        if not FileManager.Exists(path):
            return {}
        try:
            with FileManager.OpenFile(path, read=True) as file:
                content = json.loads(file.Read())
            return content if isinstance(content, dict) else {}
        except (ValueError, OSError):
            return {}

    @staticmethod
    def _SaveFallbackIndex(index: Dict[str, str]) -> None:
        path = Cache._FallbackIndexPath()
        try:
            FileManager.MakeDir(FileManager.GetDirName(path))
            with FileManager.OpenFile(path, write=True) as file:
                file.Write(json.dumps(index, indent=4, sort_keys=True))
        except OSError as error:
            Log.Warn(CATEGORY_NAME, f"Could not write {path}: {error}")

    @staticmethod
    def _RememberFallback(card_id: str, url: str) -> None:
        index = Cache._LoadFallbackIndex()
        if index.get(card_id) == url:
            return
        index[card_id] = url
        Cache._SaveFallbackIndex(index)

    @staticmethod
    def _ForgetFallback(card_id: str) -> None:
        index = Cache._LoadFallbackIndex()
        if card_id in index:
            del index[card_id]
            Cache._SaveFallbackIndex(index)

    @staticmethod
    def SetCache(card_id: str, data: bytes):
        Cache.cache[card_id] = data

    @staticmethod
    def _GetSourceCardId(site: str, card_id: str) -> str:
        if "cerebrodatastorage.blob.core.windows.net" not in site.lower():
            return card_id
        if len(card_id) != 6 or card_id[:-1] not in CEREBRO_REVERSED_IDENTITY_BASE_IDS:
            return card_id
        if card_id[-1] == "a":
            return f"{card_id[:-1]}b"
        if card_id[-1] == "b":
            return f"{card_id[:-1]}a"
        return card_id

    @staticmethod
    def _GetPersistentCacheName(card_id: str) -> str:
        if len(card_id) == 6 and card_id[:-1] in CEREBRO_REVERSED_IDENTITY_BASE_IDS:
            return f"{card_id}.{CEREBRO_SIDE_CACHE_REVISION}"
        return card_id

    ################################################################################
    # Downloading
    @staticmethod
    def IsCardId(text: str) -> bool:
        import re
        # Five digits, optionally followed by a face letter.
        return bool(re.match(r'^\d{5}[a-z]?$', text))

    @staticmethod
    def Download(url: str, save_as: str, *, expected_missing: bool = False) -> bytes|None:
        """Fetch one image and put it in the download cache.

        Returns the bytes, or None if the URL did not answer with one.

        `expected_missing` is for the cards we already know the servers do not
        carry: asking them anyway is how the better picture eventually arrives,
        and a 404 there is the answer, not a fault. Without it every card in the
        fallback map would file two warnings a day, for months.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        try:
            Log.DebugInfo(CATEGORY_NAME, f"Downloading from {url}")
            response = requests.get(url, headers=headers, timeout=3)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type')
            ext_name = "bmp"
            if content_type:
                if 'image/jpeg' in content_type:
                    ext_name = "jpg"
                elif 'image/png' in content_type:
                    ext_name = "png"
                elif 'image/webp' in content_type:
                    ext_name = "webp"

            Log.DebugInfo(CATEGORY_NAME, f"Downloaded: {save_as}")
            data = response.content
            file_path = FileManager.JoinPath(CACHE_FOLDER.value, f"{save_as}.{ext_name}")
            FileManager.MakeDir(FileManager.GetDirName(file_path))
            with FileManager.OpenFile(file_path, write=True, bin=True) as file:
                file.Write(data)
            # A card that arrives as a .png today may have been a .jpg
            # yesterday. Without this the old extension stays on disk and wins
            # the next time the folder is read.
            Cache._RemoveOtherExtensions(save_as, ext_name)
            return data
        except requests.exceptions.Timeout:
            report = Log.DebugInfo if expected_missing else Log.Warn
            report(CATEGORY_NAME, f"Timeout occurred while downloading {save_as}")
        except requests.exceptions.RequestException as error:
            report = Log.DebugInfo if expected_missing else Log.Warn
            report(CATEGORY_NAME, f"Request failed with error: {error}")
        return None

    @staticmethod
    def _RemoveOtherExtensions(save_as: str, keep: str) -> None:
        for ext_name in ("webp", "jpg", "png", "bmp"):
            if ext_name == keep:
                continue
            path = FileManager.JoinPath(CACHE_FOLDER.value, f"{save_as}.{ext_name}")
            if FileManager.Exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    @staticmethod
    def DownloadFromServers(card_id: str, save_as: str) -> bytes|None:
        """Try every configured image server, in the order they are listed."""
        # A card the fallback map covers is one the servers are already known
        # not to have, so their refusal is not news.
        expected_missing = card_id in Cache.GetFallbackImages()
        for site in IMAGE_SERVERS.value:
            source_card_id = Cache._GetSourceCardId(site, card_id)
            url = site.replace('{card_id}', source_card_id)
            url = url.replace('{card_id:U}', source_card_id.upper())
            data = Cache.Download(url, save_as, expected_missing=expected_missing)
            if data is not None:
                return data
        return None

    @staticmethod
    def RefreshFallbackImages() -> Dict[str, int]:
        """Ask the servers again for anything currently served from the map.

        Fan sites publish scans of a new pack months before Cerebro and
        MarvelCDB do. This is what lets the better picture arrive on its own:
        every card still being served from the fallback map is offered to the
        servers again, and the first one that answers replaces it. The index
        shrinks each time, so a table that is fully covered does no work at all.
        """
        index = Cache._LoadFallbackIndex()
        if not index:
            return {'checked': 0, 'upgraded': 0}

        upgraded = 0
        for card_id in sorted(index):
            if not Cache.IsCardId(card_id):
                Cache._ForgetFallback(card_id)
                continue
            data = Cache.DownloadFromServers(
                card_id,
                Cache._GetPersistentCacheName(card_id),
            )
            if data is None:
                continue
            upgraded += 1
            Cache._ForgetFallback(card_id)
            # Drop the decoded copy too, or this session keeps handing out the
            # scan it already has in memory.
            Cache.cache.pop(card_id, None)
            Log.Info(
                CATEGORY_NAME,
                f"Card {card_id}: replaced the stand-in art with a published scan.",
            )

        return {'checked': len(index), 'upgraded': upgraded}

    @staticmethod
    def LoadImage(card_id: str) -> bytes:
        # if url in ['enthralled_minion', 'minion', 'ultron_facedown_drone']:
        #     url = 'player'
        card_id = card_id.lstrip("/")

        if card_id in Cache.cache:
            return Cache.cache[card_id]

        assert card_id != "", f"{card_id=}"
        file_name = card_id

        local_folders = IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value]
        persistent_cache_name = Cache._GetPersistentCacheName(file_name)

        def try_load_image_data(image_data: bytes):
            # Status artwork is already authored in its final landscape
            # orientation. Keep its PNG bytes intact; the browser rotates it
            # clockwise inside the portrait status-card frame.
            if file_name in STATUS_TEXTURES:
                return image_data
            return ImageLib.TryRotateImage(image_data)

        # Load the image from the cache and images
        def try_load_image_path(file_path: str) -> bytes|None:
            if file_name in STATUS_TEXTURES:
                extensions = [".png", ".webp", ".jpg"]
            else:
                extensions = [".webp", ".jpg", ".png"]
            for ext_name in extensions:
                check_path = file_path + ext_name
                if FileManager.Exists(check_path):
                    with FileManager.OpenFile(check_path, read=True, bin=True) as file:
                        return try_load_image_data(file.Read())
            return None

        def try_load_image_name(name: str, folders: Sequence[str]) -> bytes|None:
            for cache_folder in folders:
                file_paths: List[str] = []
                file_paths.append(f"{cache_folder}/{name}")
                for file_path in file_paths:
                    image_data = try_load_image_path(file_path)
                    if image_data:
                        return image_data
            return None

        # User-provided images use the engine's canonical ids and always win.
        image_data = try_load_image_name(file_name, local_folders)
        if not image_data:
            # A revised key deliberately bypasses pre-fix Cerebro files that
            # may already be present under the old canonical cache name.
            image_data = try_load_image_name(
                persistent_cache_name,
                [CACHE_FOLDER.value],
            )
        if image_data:
            Cache.SetCache(file_name, image_data)
            return image_data

        if file_name in Cache.link_pic:
            image_data = Cache.LoadImage(Cache.link_pic[file_name])
            if image_data:
                return image_data

        if Cache.IsCardId(card_id):
            # Load the image from the internet
            skip_break = not BREAK_WHEN_LOAD_ONLINE_IMAGE.value
            if not skip_break:
                Debug.DebugBreak()

            data = Cache.DownloadFromServers(card_id, persistent_cache_name)
            if data is not None:
                # It came from a server, so any older fallback copy of this card
                # has just been replaced and the index entry is stale.
                Cache._ForgetFallback(card_id)
                image_data = try_load_image_data(data)
                Cache.SetCache(file_name, image_data)
                return image_data

            # Only now: art the servers do not have. Recorded so the recurring
            # refresh knows to keep asking them for something better.
            url = Cache.GetFallbackImages().get(card_id)
            if url:
                data = Cache.Download(url, persistent_cache_name)
                if data is not None:
                    Cache._RememberFallback(card_id, url)
                    image_data = try_load_image_data(data)
                    Cache.SetCache(file_name, image_data)
                    return image_data

        # raise Exception(f"Failed to load {file_name} from the internet")
        image_data = ImageCreator.CreateNoImage(card_id)
        Cache.SetCache(file_name, image_data)
        return image_data
