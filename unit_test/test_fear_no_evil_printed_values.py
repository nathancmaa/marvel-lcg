"""Fear No Evil printed values that the sdolle1775 fork checked against scans.

Only the values where the two forks differed and that fork's tests assert
the scan are pinned here. Disputed texts are left alone.
"""

import json
import unittest

from engine import Engine  # noqa: F401 - project import order

from unit_test.fne_headless import ROOT, build_scene, initialize_database, play


def papers():
    return {card["card_id"]: card for card in json.loads((ROOT / "data/cards.json").read_text(encoding="utf-8"))["fne"]}


def encounters(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))["encounters"]


class PrintedValueTests(unittest.TestCase):

    def test_disasters_are_crisis_environments_and_the_bridge_is_a_hazard(self):
        cards = papers()
        for card_id in ("60177", "60178", "60179"):
            self.assertEqual(cards[card_id]["desc"]["Crisis"], "1")
            self.assertEqual(cards[card_id]["desc"]["Boost"], "2")
        self.assertEqual(
            cards["60180"]["desc"],
            {"StartingThreat": "1*", "Hinder": "2*", "Hazard": "1", "Boost": "2"},
        )
        self.assertNotIn("Crisis", cards["60180"]["text"])

    def test_scan_checked_encounter_values(self):
        cards = papers()
        expected = {
            ("60189", "Acceleration"): "1",
            ("60189", "StartingThreat"): "2*",
            ("60149", "Boost"): "4",
            ("60075", "Boost"): "3",
            ("60174", "Boost"): "3",
            ("60165", "Boost"): "1*",
            ("60168", "Boost"): "1*",
            ("60073", "Hazard"): "1",
            ("60073", "Boost"): "1",
            ("60187", "THW+"): "1",
            ("60090", "Boost"): "1",
            ("60126", "Boost"): "0",
            ("60193", "Boost"): "0",
            ("60198", "Boost"): "0",
            ("60195", "SCH+"): "2",
            ("60196", "ATK+"): "2",
            ("60054", "MaxPerUnit"): "1",
        }
        for (card_id, key), value in expected.items():
            with self.subTest(card=card_id, key=key):
                self.assertEqual(cards[card_id]["desc"].get(key), value)
        self.assertNotIn("Crisis", cards["60189"]["desc"])
        for card_id in ("60134b", "60135b", "60136b", "60137b", "60138b"):
            self.assertEqual(cards[card_id]["desc"]["TargetThreat"], "10")
            self.assertEqual(cards[card_id]["desc"]["EscalationThreat"], "1")

    def test_our_stage_numbers_and_art_modifiers_are_kept(self):
        cards = papers()
        # 60073 reads printed_stage as a number; the art cards modify SCH/THW.
        self.assertEqual(cards["60065"]["desc"]["Stage"], "1")
        self.assertEqual(cards["60122"]["desc"]["SCH+"], "1")
        self.assertEqual(cards["60122"]["desc"]["THW+"], "1")

    def test_card_counts(self):
        for path in ("data/scenarios/art_museum_heist.json", "data/scenarios/art_museum_heist_expert.json"):
            self.assertEqual(encounters(path).count("60126"), 2)
        cops = encounters("data/encounter_sets/cops.json")
        self.assertEqual(cops.count("60182"), 2)
        self.assertEqual(cops.count("60183"), 1)


class CrisisOnTheTableTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def thwart_targets(self, card_id):
        run = play(
            build_scene("the_getaway", "bullseye", ["spider_man"], 21),
            ['Puzzle.ChangeFormFor(0, "Identity")', f'Puzzle.PutIntoPlay("{card_id}")', "Puzzle.End()"],
            render=False,
        )
        self.assertEqual(run.Exceptions(), [])
        world = run.world
        main = [face for face in world.FindCardsOnField() if face.paper.card_id == "60128b"][0]
        other = [face for face in world.FindCardsOnField() if face.paper.card_id == card_id][0]
        targets = next(
            option.get("all_legal_targets", [])
            for option in reversed(run.devices.prompts[-1].options)
            if option.get("name") == "Thwart"
        ) if any(option.get("name") == "Thwart" for option in run.devices.prompts[-1].options) else []
        return main.card.object_id in targets, other

    def test_a_disaster_blocks_thwarting_the_main_scheme(self):
        main_thwartable, disaster = self.thwart_targets("60177")
        self.assertEqual(disaster.crisis, 1)
        self.assertFalse(main_thwartable)

    def test_collapsing_bridge_does_not(self):
        main_thwartable, bridge = self.thwart_targets("60180")
        self.assertEqual(bridge.crisis, 0)
        self.assertTrue(main_thwartable)


if __name__ == "__main__":
    unittest.main()
