"""Red Skull campaign: per-player tech-upgrade removal and Improved conditions.

Ported from the sdolle1775 fork (f7e1678), in real four-hero games.
"""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - establishes project import order
from engine.log import Log
from game.scene import SceneLoader
from game.test.headless import HeadlessDeviceManager
from game.test.harness import initialize_database, run_scene_with_devices
from game.world.world_render import WorldRender


TECH_IDS = ("04155", "04156", "04157", "04158")
BASIC_IDS = ("04159a", "04160a", "04161a", "04162a")


class TestRedSkullRemovedTech(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setup_campaign(self, scenario="absorbing_man", *, removed_players=None, deck_copies=False,
                       campaign=True, expert=False, selected=TECH_IDS,
                       basic_selected=("04159a", "", "", ""), improved_players=None):
        scene = SceneLoader.NewScene(
            scenario, None, ["iron_man", "spider_man", "captain_marvel", "hawkeye"], 103,
        )
        scene.campaign.campaign_id = "rise_of_red_skull" if campaign else ""
        scene.campaign.expert = expert
        scene.rules = ["v18_all"] + (["mode_campaign"] if campaign else [])
        scene.campaign.campaign_log = {
            **{f"Player {index + 1} Tech Upgrade": card_id for index, card_id in enumerate(selected) if card_id},
            **{f"Player {index + 1} Basic Upgrade": card_id for index, card_id in enumerate(basic_selected) if card_id},
        }
        if removed_players is not None:
            for player_number in range(1, 5):
                scene.campaign.campaign_log[f"Player {player_number} tech upgrade removed from campaign"] = (
                    "Yes" if player_number in removed_players else ""
                )
        if improved_players is not None:
            for player_number in range(1, 5):
                scene.campaign.campaign_log[f"Player {player_number} Basic Condition replaced with Improved side"] = (
                    "Yes" if player_number in improved_players else ""
                )
        if deck_copies:
            for player in scene.players:
                player.player_deck += list(TECH_IDS)
        devices = HeadlessDeviceManager(stop_when=lambda prompt: prompt.event_name == "WhenPlayerInTurn")
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch.object(WorldRender, "ErrorOccurred") as errors,
            patch.object(Log, "Warn") as warnings,
        ):
            game = run_scene_with_devices(scene, devices)
        errors.assert_not_called()
        warnings.assert_not_called()
        self.assertIsNotNone(devices.stopped_prompt)
        return game.world

    def test_removed_choices_are_not_added_in_later_campaign_scenarios(self):
        # Each run is a real four-hero game; one standard and one expert
        # scenario keep the suite quick.
        for scenario, expert in (("absorbing_man", False), ("zola", True)):
            with self.subTest(scenario=scenario, expert=expert):
                world = self.setup_campaign(scenario, removed_players=(1, 3), expert=expert)
                for index, player in enumerate(world.const_seat_order_players):
                    card_id = TECH_IDS[index]
                    found = player.GetControlUpgrade()
                    self.assertEqual(
                        sum(face.paper.card_id == card_id for face in found),
                        0 if card_id in ("04155", "04157") else 1,
                    )
                self.assertEqual(len(world.FindCardsOnField(name="04159a")), 1)
                self.assertFalse(any(card.face.paper.card_id in ("04155", "04157")
                                     for card in world.object_manager.card_dict.values()))

    def test_only_each_players_selected_copies_are_removed_even_after_printed_setup(self):
        for scenario in ("absorbing_man",):
            with self.subTest(scenario=scenario):
                world = self.setup_campaign(scenario, removed_players=(1, 2, 3, 4), deck_copies=True)
                copies = [card.face for card in world.object_manager.card_dict.values()
                          if card.face.paper.card_id in TECH_IDS]
                self.assertEqual(len(copies), 16)
                for face in copies:
                    is_selected = face.paper.card_id == TECH_IDS[face.GetOwnerPlayer().player_id]
                    self.assertEqual(face.IsInPlay(), not is_selected)
                    self.assertEqual(face.card.area.flags.is_removed, is_selected)
                for index, player in enumerate(world.const_seat_order_players):
                    self.assertFalse(any(face.paper.card_id == TECH_IDS[index] for face in player.hand_cards.Get()))
                    self.assertFalse(any(face.paper.card_id == TECH_IDS[index] for face in player.player_deck.Get()))

    def test_removal_setting_does_not_affect_standard_games(self):
        world = self.setup_campaign(removed_players=(1, 2, 3, 4), deck_copies=True, campaign=False)
        for player in world.const_seat_order_players:
            in_play = {face.paper.card_id for face in player.GetControlUpgrade()}
            self.assertTrue(set(TECH_IDS).issubset(in_play))

    def test_removing_one_players_upgrade_keeps_another_players_copy_of_the_same_card(self):
        world = self.setup_campaign(
            removed_players=(1,), deck_copies=True, selected=("04155", "04155", "04157", "04158"),
        )
        player1, player2 = world.const_seat_order_players[:2]
        self.assertFalse(any(face.paper.card_id == "04155" for face in player1.GetControlUpgrade()))
        self.assertTrue(any(face.paper.card_id == "04155" for face in player2.GetControlUpgrade()))
        self.assertTrue(any(face.paper.card_id == "04156" for face in player1.GetControlUpgrade()))

    def assert_basic_sides(self, world, expected):
        for index, player in enumerate(world.const_seat_order_players):
            conditions = [face for face in player.GetControlUpgrade()
                          if face.paper.card_id[:5] in ("04159", "04160", "04161", "04162")]
            self.assertEqual([face.paper.card_id for face in conditions], [expected[index]] if expected[index] else [])
            if conditions:
                self.assertIs(conditions[0].bind_face, player.GetIdentity())
                self.assertEqual(player.GetIdentity().max_health - player.GetIdentity().printed_health,
                                 {"04159": 2, "04160": 1, "04161": 3, "04162": 4}[expected[index][:5]])

    def test_basic_conditions_use_the_matching_improved_side_independently_per_player(self):
        for improved_players in ((1, 3),):
            with self.subTest(improved_players=improved_players):
                world = self.setup_campaign(
                    basic_selected=BASIC_IDS, improved_players=improved_players, removed_players=(1, 3),
                )
                expected = [card_id[:5] + ("b" if index + 1 in improved_players else "a")
                            for index, card_id in enumerate(BASIC_IDS)]
                self.assert_basic_sides(world, expected)
                for index, player in enumerate(world.const_seat_order_players):
                    self.assertEqual(any(face.paper.card_id == TECH_IDS[index] for face in player.GetControlUpgrade()),
                                     index + 1 not in (1, 3))
                    self.assertEqual(world.scene.campaign.campaign_log[f"Player {index + 1} Basic Upgrade"], BASIC_IDS[index])

    def test_improved_conditions_work_in_standard_and_expert_later_scenarios(self):
        for scenario, expert in (("red_skull", True),):
            with self.subTest(scenario=scenario, expert=expert):
                world = self.setup_campaign(
                    scenario, expert=expert, basic_selected=BASIC_IDS, improved_players=(1, 2, 3, 4),
                )
                self.assert_basic_sides(world, [card_id[:5] + "b" for card_id in BASIC_IDS])

    def test_basic_improvement_does_not_apply_outside_campaign_or_before_reward(self):
        for scenario, campaign in (("crossbones", True),):
            with self.subTest(scenario=scenario, campaign=campaign):
                world = self.setup_campaign(
                    scenario, campaign=campaign, basic_selected=BASIC_IDS, improved_players=(1, 2, 3, 4),
                )
                self.assert_basic_sides(world, ("",) * 4)


if __name__ == "__main__":
    unittest.main()
