from pathlib import Path
import unittest

from build import Build
from engine.lib.version import Ver


ROOT = Path(__file__).resolve().parents[1]


class V18SetupUiTests(unittest.TestCase):

    def test_ronin_edition_release_identity_is_consistent(self):
        """The strings the UI shows agree with the numbers they come from.

        Written against the literal 0.6.1 it was cut at, this went stale the
        moment 0.7.0 landed and stayed red through four releases, asserting a
        version nothing had shipped for weeks. Deriving the expectations means
        it checks that the pieces agree rather than that they have not moved,
        so it survives a bump and still catches a half-done one.
        """
        Ver.Initialize()

        self.assertEqual(
            Build.PRODUCT_NAME,
            'Marvel Champions Digital: Ronin Edition',
        )
        self.assertEqual(
            Build.RELEASE_VERSION,
            f'{Build.MAJOR}.{Build.MINOR}.{Build.PATCH}',
        )
        self.assertEqual(
            str(Ver.version),
            f'{Build.RELEASE_VERSION}.{Build.BUILD}',
        )
        self.assertEqual(
            Ver.ui_version_str,
            f"{Ver.version}{'r' if Build.release else 'd'}",
        )
        self.assertEqual(
            Ver.release_label,
            f'Version {Build.RELEASE_VERSION} — “{Build.RELEASE_CODENAME}”',
        )

    def test_the_changelog_names_the_version_being_built(self):
        """A version bump that misses the docs is the failure worth catching.

        The number lives in build.py and is repeated by hand in the changelog
        banner, so the two can drift silently -- and did, briefly, while these
        releases were renumbered.
        """
        changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')

        self.assertIn(
            f'> Current release version: {Build.RELEASE_VERSION} '
            f'— “{Build.RELEASE_CODENAME}”',
            changelog,
        )

    def test_start_page_displays_ronin_edition_and_echo_release(self):
        source = (ROOT / 'public/main.html').read_text(encoding='utf-8')

        self.assertIn('Marvel Champions Digital: Ronin Edition', source)
        self.assertIn('<h1>Marvel Champions Digital</h1>', source)
        self.assertIn('<h2>Ronin Edition</h2>', source)
        self.assertIn('Version 0.6.1 — “Echo”', source)
        self.assertIn('Based on', source)
        self.assertIn('Marvel Champions: Digital Edition', source)
        self.assertIn('by Irefrixs', source)

    def test_quick_game_uses_only_v18_rules(self):
        source = (ROOT / "public/js/solo.ts").read_text(encoding="utf-8")

        self.assertIn("rules: ['v18_all']", source)
        self.assertNotIn("v16_all", source)
        self.assertNotIn("encounter_cards_ignore_crisis", source)

    def test_campaign_uses_v18_campaign_rules(self):
        source = (ROOT / "public/js/campaign.ts").read_text(encoding="utf-8")

        self.assertIn("'mode_campaign'", source)
        self.assertIn("'v18_all'", source)
        self.assertNotIn("v16_all", source)
        self.assertNotIn("encounter_cards_ignore_crisis", source)

    def test_advanced_setup_has_no_rules_compatibility_controls(self):
        source = (ROOT / "public/scene.html").read_text(encoding="utf-8")

        self.assertIn("new_game.rules.push('v18_all')", source)
        self.assertNotIn('id="rules"', source)
        self.assertNotIn("new_game.rules.push('no_encounter_cards_ignore_crisis')", source)
        self.assertNotIn("new_game.rules.push('no_crisis_of_infinite_deadpools')", source)

    def test_statistics_notifications_are_off_by_default(self):
        settings = (ROOT / "public/js/marvel/settings.ts").read_text(encoding="utf-8")
        setup = (ROOT / "public/scene.html").read_text(encoding="utf-8")

        self.assertIn(
            "static statistics_off = !search_params.has('notification')",
            settings,
        )
        self.assertIn(
            '<option selected="selected" value="0">Off</option>',
            setup,
        )
        self.assertIn(
            "formData.statistics_notification = '0'",
            setup,
        )

    def test_game_table_uses_an_explicit_route(self):
        server = (
            ROOT / "engine/device/web/server/server_files.py"
        ).read_text(encoding="utf-8")
        solo = (ROOT / "public/js/solo.ts").read_text(encoding="utf-8")
        campaign = (ROOT / "public/js/campaign.ts").read_text(encoding="utf-8")
        replay = (ROOT / "public/replay.html").read_text(encoding="utf-8")

        self.assertIn("self.AddAwaitGetSecurity('/', self.handle_main)", server)
        self.assertIn("self.AddAwaitGetSecurity('/table', self.handle_marvel)", server)
        self.assertNotIn("request.query_string", server)
        self.assertIn("window.location.assign('/table?p=0')", solo)
        self.assertIn("window.location.assign('/table?p=0')", campaign)
        self.assertIn("let gameUrl = '/table?hot_seat&3d_scene'", replay)

    def test_start_page_can_continue_the_single_server_session(self):
        source = (ROOT / 'public/main.html').read_text(encoding='utf-8')
        server = (
            ROOT / 'engine/device/web/server/server_new_game.py'
        ).read_text(encoding='utf-8')
        world = (ROOT / 'game/world/world.py').read_text(encoding='utf-8')

        self.assertIn('id="continue-game"', source)
        self.assertIn("fetch('/active_session')", source)
        self.assertIn("fetch('/continue_game', {method: 'POST'})", source)
        self.assertIn("window.location.assign('/table?p=0')", source)
        self.assertIn("self.AddAwaitGetSecurity('/active_session'", server)
        self.assertIn("self.AddPostSecurity('/continue_game'", server)
        self.assertIn('self.controller_manager.game.SaveActiveSession()', world)

        solo_page = (ROOT / 'public/solo.html').read_text(encoding='utf-8')
        campaign_page = (ROOT / 'public/campaign.html').read_text(encoding='utf-8')
        self.assertIn('/public/js/solo.js?ronin-session=1', solo_page)
        self.assertIn('/public/js/campaign.js?ronin-session=1', campaign_page)


if __name__ == "__main__":
    unittest.main()
