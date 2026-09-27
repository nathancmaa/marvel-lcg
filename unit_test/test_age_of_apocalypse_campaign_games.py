"""Age of Apocalypse campaign setup in real games (headless, nothing mocked)."""

import contextlib
import io
import unittest

from engine import Engine  # noqa: F401 - project import order

from game.scene import SceneLoader
from game.test.harness import initialize_database, run_scene_with_devices
from game.test.headless import HeadlessDeviceManager


def _play_to_first_turn(scenario, seed, log=None, *, expert=False):
    scene = SceneLoader.NewScene(scenario, None, ["spider_man"], seed)
    scene.campaign.campaign_id = "age_of_apocalypse"
    scene.campaign.expert = expert
    scene.rules = ["v18_all", "mode_campaign"]
    scene.campaign.campaign_log = dict(log or {})
    devices = HeadlessDeviceManager(
        stop_when=lambda prompt: prompt.event_name == "WhenPlayerInTurn")
    with contextlib.redirect_stdout(io.StringIO()):
        game = run_scene_with_devices(scene, devices)
    return game, devices


class AgeOfApocalypseCampaignGameTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_a_prelate_in_play_is_never_also_the_overseer(self):
        # Scenario 3 puts Prelates into play; their reverse is an Overseer,
        # which used to be picked again for the mission on these seeds.
        for seed in (205, 209, 214):
            with self.subTest(seed=seed):
                game, devices = _play_to_first_turn("apocalypse", seed)
                self.assertIsNotNone(devices.stopped_prompt)
                world = game.world
                prelates = {face.name for face in world.FindCardsOnField(trait="PRELATE")}
                overseers = {
                    face.name for face in world.area_mission.Get()
                    if face.HasTrait("OVERSEER")
                }
                self.assertEqual(len(overseers), 1)
                self.assertFalse(prelates & overseers)

    def test_removed_missions_are_not_drawn_again(self):
        log = {
            "Mission Side Schemes Removed from campaign": "45166a;45167a;45168a",
            "Mission Side Schemes Defeated": "45166a",
        }
        game, _ = _play_to_first_turn("four_horsemen", 301, log)
        missions = [
            face.paper.card_id for face in game.world.area_schemes_side.Get()
            if face.HasTrait("MISSION")
        ]
        self.assertEqual(missions, ["45169a"])


if __name__ == "__main__":
    unittest.main()
