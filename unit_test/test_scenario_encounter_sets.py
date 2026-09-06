import json
import re
from pathlib import Path
import unittest

from engine import Engine  # noqa: F401 - establishes the project's import order
from engine.lib.version import Ver
from game.scene.loader import SceneLoader


class TestScenarioEncounterSets(unittest.TestCase):

    project_root = Path(__file__).resolve().parents[1]

    def test_required_sets_are_restored_when_client_omits_them(self):
        merged = SceneLoader.MergeEncounterSets(
            ["prelates", "standard"],
            ["standard"],
        )

        self.assertEqual(merged, ["prelates", "standard"])

    def test_selected_modular_sets_are_retained_without_duplicates(self):
        merged = SceneLoader.MergeEncounterSets(
            ["prelates", "standard"],
            ["standard", "dark_riders", "infinites", "dark_riders"],
        )

        self.assertEqual(
            merged,
            ["prelates", "standard", "dark_riders", "infinites"],
        )

    def test_selected_standard_variant_replaces_the_scenario_default(self):
        merged = SceneLoader.MergeEncounterSets(
            ["prelates", "standard", "expert"],
            ["standard_iii", "expert", "dark_riders", "infinites"],
        )

        self.assertEqual(
            merged,
            ["prelates", "standard_iii", "expert", "dark_riders", "infinites"],
        )

    def test_selected_expert_variant_replaces_the_scenario_default(self):
        merged = SceneLoader.MergeEncounterSets(
            ["standard", "expert"],
            ["standard", "expert_ii"],
        )

        self.assertEqual(merged, ["standard", "expert_ii"])

    def test_only_the_last_selected_variant_from_each_family_is_retained(self):
        merged = SceneLoader.MergeEncounterSets(
            ["prelates", "standard", "expert"],
            ["standard", "standard_iii", "expert", "expert_ii"],
        )

        self.assertEqual(merged, ["prelates", "standard_iii", "expert_ii"])

    def test_default_modular_sets_are_merged_without_duplicates(self):
        merged = SceneLoader.MergeEncounterSets(
            ["standard", "scientist_supreme"],
            ["scientist_supreme", "shield"],
        )

        self.assertEqual(merged, ["standard", "scientist_supreme", "shield"])

    def test_scene_loader_enforces_required_sets_from_scenario_json(self):
        Ver.Initialize()
        campaign = {
            "version": "0.6.0",
            "campaign_id": "agents_of_shield",
            "name": "Baron Zemo",
            "villain": ["50165a,50165b"],
            "schemes": ["50167a,50167b"],
            "encounter_sets": [
                "standard",
                "shield_executive_board",
                "executive_board_evidence",
            ],
            "modular_sets": ["scientist_supreme", "shield"],
        }

        scene = SceneLoader.NewFromJson(
            json.dumps(campaign),
            ["standard_iii", "shield"],
            [],
            1,
            ["v18_all"],
            {},
        )

        self.assertEqual(
            scene.campaign.encounter_sets,
            [
                "standard_iii",
                "shield_executive_board",
                "executive_board_evidence",
                "shield",
            ],
        )

    def test_quick_game_offers_only_standard_sets_that_exist(self):
        """The picker names its Standard sets in markup, not from the data.

        Nothing else ties the three options in solo.html to the files they
        stand for, so an option naming a set that was never shipped would
        reach the engine and fail there instead of here.
        """
        markup = (self.project_root / "public" / "solo.html").read_text(
            encoding="utf-8"
        )
        select = re.search(
            r'<select id="standard-set">(.*?)</select>', markup, re.DOTALL
        )
        self.assertIsNotNone(select, "solo.html has no #standard-set picker")
        offered = re.findall(r'value="([^"]+)"', select.group(1))

        self.assertEqual(offered, ["standard", "standard_ii", "standard_iii"])
        for encounter_set in offered:
            with self.subTest(encounter_set=encounter_set):
                self.assertEqual(
                    SceneLoader.GetEncounterSetFamily(encounter_set), "standard"
                )
                path = (
                    self.project_root
                    / "data"
                    / "encounter_sets"
                    / f"{encounter_set}.json"
                )
                self.assertTrue(path.is_file())
                self.assertTrue(
                    json.loads(path.read_text(encoding="utf-8")).get("encounters")
                )

    def test_all_scenarios_reference_existing_required_encounter_sets(self):
        sets_info = json.loads(
            (self.project_root / "data" / "sets_info.json").read_text(
                encoding="utf-8"
            )
        )
        listed_sets = {
            encounter_set
            for pack in sets_info.values()
            if isinstance(pack, dict)
            for encounter_set in pack.get("encounters", [])
        }
        encounter_sets_folder = self.project_root / "data" / "encounter_sets"
        scenario_files = sorted(
            (self.project_root / "data" / "scenarios").glob("*.json")
        )

        self.assertGreater(len(scenario_files), 0)
        for scenario_file in scenario_files:
            with self.subTest(scenario=scenario_file.name):
                scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
                for encounter_set in scenario.get("encounter_sets", []):
                    self.assertIn(encounter_set, listed_sets)
                    encounter_set_file = encounter_sets_folder / f"{encounter_set}.json"
                    self.assertTrue(encounter_set_file.is_file())
                    encounter_set_data = json.loads(
                        encounter_set_file.read_text(encoding="utf-8")
                    )
                    self.assertTrue(encounter_set_data.get("encounters"))


if __name__ == "__main__":
    unittest.main()
