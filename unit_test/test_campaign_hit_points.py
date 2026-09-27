"""Hero hit points between campaign scenarios, in real games.

The campaign guides carry damage over only in an expert campaign: a standard
campaign starts every scenario at full health whatever the log says.
"""

import contextlib
import io
import unittest

from engine import Engine  # noqa: F401 - project import order

from game.scene import SceneLoader
from game.test.harness import initialize_database, run_scene_with_devices
from game.test.headless import HeadlessDeviceManager


def _identity_health_at_first_prompt(scenario, log, *, expert):
    scene = SceneLoader.NewScene(scenario, None, ["spider_man"], 103)
    scene.campaign.campaign_id = "rise_of_red_skull"
    scene.campaign.expert = expert
    scene.rules = ["v18_all", "mode_campaign"]
    scene.campaign.campaign_log = dict(log)
    seen = []

    def stop(prompt):
        # Campaign setup has run by the first prompt that follows it: the
        # expert heal offer, the mulligan or the first turn.
        identity = Engine.game.world.GetFirstPlayer().GetIdentity()
        seen.append((identity.health, identity.max_health))
        return True

    devices = HeadlessDeviceManager(stop_when=stop)
    with contextlib.redirect_stdout(io.StringIO()):
        run_scene_with_devices(scene, devices)
    return seen[0]


class CampaignHitPointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_standard_campaign_starts_at_full_health(self):
        health, maximum = _identity_health_at_first_prompt(
            "absorbing_man", {"Player 1 Remaining hit points": "5"}, expert=False)
        self.assertEqual(health, maximum)

    def test_expert_campaign_carries_the_logged_hit_points(self):
        health, _ = _identity_health_at_first_prompt(
            "absorbing_man_expert", {"Player 1 Remaining hit points": "5"}, expert=True)
        self.assertEqual(health, 5)

    def test_expert_campaign_hero_logged_at_zero_was_defeated(self):
        # Not "unset": the hero does not come back at full for nothing.
        health, maximum = _identity_health_at_first_prompt(
            "absorbing_man_expert", {"Player 1 Remaining hit points": "0"}, expert=True)
        self.assertEqual(health, 1)
        self.assertLess(health, maximum)


if __name__ == "__main__":
    unittest.main()
