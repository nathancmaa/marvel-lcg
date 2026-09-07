from core import *
from engine.device.web.server.server_base import GameServerBase

CATEGORY_NAME = "WEB"

class GameServerHTML(GameServerBase):

    @override
    def __init__(self) -> None:
        super().__init__()

        self.AddHtmlSecurity('/main', './public/main.html')
        self.AddHtmlSecurity('/deck', './public/deck.html')
        self.AddHtmlSecurity('/deck-viewer', './public/deck-viewer.html')
        self.AddHtmlSecurity('/cards', './public/cards.html')
        self.AddHtmlSecurity('/solo', './public/solo.html')
        self.AddHtmlSecurity('/campaign', './public/campaign.html')
        self.AddHtmlSecurity('/scene', './public/scene.html')
        self.AddHtmlSecurity('/replay', './public/replay.html')
        self.AddHtmlSecurity('/settings', './public/settings.html')
        self.AddHtmlSecurity('/statistics', './public/statistics.html')
        self.AddHtmlSecurity('/proxy', './public/proxy.html')
        self.AddHtmlSecurity('/puzzle', './public/replay.html')
        self.AddHtmlSecurity('/credits', './public/credits.html')
        self.AddHtmlSecurity('/puzzle_editor', './public/puzzle_editor.html')
        self.AddHtmlSecurity('/puzzle_test', './public/replay.html')
        self.AddHtmlSecurity('/report', './public/report.html')
        # In public/ rather than assets/textures/, because assets is a bind
        # mount in the Docker deployment and a mount shadows whatever the image
        # was built with. The wallpaper is part of the app, not user data, so
        # shipping it under assets meant a git pull could never deliver it: the
        # new file went into the image where the mount hid it.
        self.AddHtmlSecurity(
            '/background.webp',
            './public/background.webp',
        )
