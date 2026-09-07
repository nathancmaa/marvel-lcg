from pathlib import Path
import unittest

from build import Build
from engine.lib.version import Ver


ROOT = Path(__file__).resolve().parents[1]


class V18SetupUiTests(unittest.TestCase):

    def test_release_identity_is_consistent(self):
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
            'Marvel Champions Digital: Cerebro',
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
        # No codename any more: the fork carries one name and releases carry
        # a number. A label that still tried to interpolate one would not
        # merely read oddly, it would fail to build.
        self.assertEqual(Ver.release_label, f'Version {Build.RELEASE_VERSION}')
        self.assertFalse(
            hasattr(Build, 'RELEASE_CODENAME'),
            'per-release codenames were dropped; RELEASE_CODENAME should be gone',
        )

    def test_the_changelog_names_the_version_being_built(self):
        """A version bump that misses the docs is the failure worth catching.

        The number lives in build.py and is repeated by hand in the changelog
        banner, so the two can drift silently -- and did, briefly, while these
        releases were renumbered.
        """
        changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')

        self.assertIn(
            f'> Current release version: {Build.RELEASE_VERSION}',
            changelog,
        )

    def test_start_page_displays_the_version_being_built(self):
        """The home page names the version, and it is the one in build.py.

        This assertion used to be the literal 0.6.1 the page was written at,
        and it passed for four releases while the page told everyone who
        opened it that they were running 0.6.1 -- a green test holding a stale
        string in place, which is worse than no test at all. Derived from
        Build, it fails the moment a version bump forgets this page.
        """
        source = (ROOT / 'public/main.html').read_text(encoding='utf-8')

        self.assertIn('Marvel Champions Digital: Cerebro', source)
        self.assertIn('<h1>Marvel Champions Digital</h1>', source)
        self.assertIn(Build.RELEASE_LABEL, source)
        # The edition is named in the page title and in the release label
        # underneath, so a heading repeating it was the third time in as many
        # lines. It is deliberately not there.
        self.assertNotIn('<h2>Ronin Edition</h2>', source)
        self.assertNotIn('<h2>Cerebro</h2>', source)

    def test_start_page_credits_the_forks_it_came_from(self):
        """Both upstreams, not just the first.

        The fork name, and the 0.6.x releases this fork continues
        from, are z00lus's work; crediting only Irefrixs skipped the fork this
        one is actually made of.
        """
        source = (ROOT / 'public/main.html').read_text(encoding='utf-8')

        self.assertIn('Based on', source)
        self.assertIn('Marvel Champions: Digital Edition', source)
        self.assertIn('by Irefrixs', source)
        self.assertIn('by z00lus', source)
        self.assertIn('https://github.com/z00lus/marvel-lcg', source)

    def test_quick_game_uses_only_v18_rules(self):
        source = (ROOT / "public/js/solo.ts").read_text(encoding="utf-8")

        # Quick Game builds its rules through heroicRules() now that Heroic is
        # offered, so the flat literal this used to look for is gone. What the
        # test is actually about survives: both branches of that builder start
        # from v18_all, and neither Quick Game nor anything it sends carries a
        # legacy rules-compatibility flag. Asserting the branches rather than
        # the call keeps it a real check -- dropping v18_all from either one
        # still fails here.
        self.assertIn("rules: heroicRules()", source)
        self.assertIn("['v18_all', `mode_heroic_${level}`]", source)
        self.assertIn("['v18_all']", source)
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

        # The two pages that take part in a session used to be asserted to
        # carry a hand-written `?ronin-session=1` on their scripts, so a
        # returning browser could not run the previous version from cache.
        # AssetVersion took that job over: ReadHtmlFile rewrites every css/js
        # reference to /v/<token>/, and the token is a content hash, so it
        # changes exactly when the file does rather than when someone
        # remembers to bump a string. The hand-written token was left behind
        # and drifted -- these lines went on asserting `ronin-session=1` long
        # after the pages had moved to `quickstart-products=2`, which is a test
        # failing for a reason that has nothing to do with what it is named
        # after. Cache busting is covered properly in test_asset_versioning.py
        # (see test_the_token_tracks_content and
        # test_a_page_is_not_cached_and_carries_the_token); it does not belong
        # here, and pinning whatever string a page happens to carry today would
        # only break again on the next bump.


if __name__ == "__main__":
    unittest.main()
