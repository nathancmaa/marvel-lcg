from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401

from cards.database import CardsDB
from engine.lib.image_creator import ImageCreator
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.card.face.card_face import CardFace
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]

LEADERS = ["57001", "57002", "57003", "57004", "57040", "57041", "57042", "57043"]
MAIN_SCHEMES = ["57005a,57005b", "57006a,57006b", "57044a,57044b", "57045a,57045b"]

# The versus-only cards: each player's own leader deck. Every one of them says
# "your leader" or "the enemy leader's main scheme", neither of which exists in
# a cooperative game, so the pack ships without them on purpose.
VERSUS_ONLY = {"57032", "57033", "57034", "57035",
               "57074", "57075", "57076", "57077"}

SYNTHEZOID_REPRINTS = {
    "57015": "56110",   # Rapid Response -- an ability link, not a full link
    "57020": "56089",   # Justice Like Lightning
    "57071": "56166",   # Atlanteans
}

FULL_LINKS = {
    "57036": "56125", "57037": "56126", "57038": "56127",
    "57039a": "56128a", "57039b": "56128b",
    "57078": "56125", "57079": "56126", "57080": "56127",
    "57081a": "56128a", "57081b": "56128b",
}

MODULAR_SETS = [
    "shield_ops", "thunderbolts", "taskmaster", "deadly_duo",
    "young_avengers", "scarlet_twins", "moon_knight", "royal_guard",
]

SCENARIOS = ["she_hulk", "she_hulk_expert", "vision", "vision_expert"]


def load_card(module: str):
    return importlib.import_module(module)


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class SynthezoidIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        ImageCreator.Initialize()

    def make_world(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(
                campaign_id="synthezoid_test",
                name="Synthezoid Test",
            ),
            players=[HeroDescriptor(
                version="",
                name="Test",
                hero=[],
                hero_deck=[],
                obligations=[],
                nemesis_set=[],
                player_deck=[],
            )],
        )
        world = World(scene, [SimpleNamespace(manager=manager)])
        world.rule.SetRule(scene.rules, False, 1)
        world.insert = CardFactory.GenerateCard(
            "rule_a,rule_b",
            world.area_insert,
            world,
            ui_render=False,
        ).face
        return world

    def test_every_card_in_the_pack_can_create_a_real_card_face(self):
        world = self.make_world()
        scenario = world.GetScenario()
        pack = read("data/cards.json")["synthezoid"]

        for entry in pack:
            card_id = entry["card_id"]
            if card_id.endswith("b") and card_id[:-1] + "a" in {
                    e["card_id"] for e in pack}:
                continue  # reached through its own front face
            with self.subTest(card_id=card_id):
                if card_id + "b" in {e["card_id"] for e in pack}:
                    card_id = "%s,%sb" % (card_id, card_id[:-1])
                area = (world.main_schemes_deck if card_id in MAIN_SCHEMES
                        else scenario.encounter_deck)
                card = CardFactory.GenerateCard(card_id, area, world, ui_render=False)
                self.assertIsInstance(card.face, CardFace)

    def test_the_versus_only_cards_are_absent_on_purpose(self):
        ids = {entry["card_id"] for entry in read("data/cards.json")["synthezoid"]}
        self.assertEqual(ids & VERSUS_ONLY, set())

        # Everything else in the printed range is here.
        expected = {"57005a", "57005b", "57006a", "57006b",
                    "57039a", "57039b", "57044a", "57044b",
                    "57045a", "57045b", "57046a", "57046b",
                    "57081a", "57081b"}
        for number in range(1, 82):
            card_id = "570%02d" % number
            if card_id in VERSUS_ONLY:
                continue
            if any(other.startswith(card_id) for other in expected):
                continue
            expected.add(card_id)
        self.assertEqual(ids, expected)

    def test_reprinted_cards_borrow_the_original_implementation(self):
        by_id = {entry["card_id"]: entry
                 for entry in read("data/cards.json")["synthezoid"]}

        for card_id, original in SYNTHEZOID_REPRINTS.items():
            with self.subTest(card_id=card_id):
                self.assertEqual(by_id[card_id].get("ability_link"), original)

        for card_id, original in FULL_LINKS.items():
            with self.subTest(card_id=card_id):
                self.assertEqual(by_id[card_id].get("full_link"), original)

        # The two main scheme fronts are the Civil War ones word for word.
        self.assertEqual(by_id["57005a"].get("ability_link"), "56063a")
        self.assertEqual(by_id["57044a"].get("ability_link"), "56063a")

    def test_the_pack_is_registered_as_a_set(self):
        entry = read("data/sets_info.json")["57. Synthezoid Smackdown"]
        self.assertEqual(entry["name"], "synthezoid")
        self.assertEqual(entry["scenarios"], ["she_hulk", "vision"])
        self.assertEqual(sorted(entry["encounters"]), sorted(MODULAR_SETS))

    def test_every_modular_set_holds_five_cards_that_exist(self):
        for name in MODULAR_SETS:
            with self.subTest(modular=name):
                encounters = read("data/encounter_sets/%s.json" % name)["encounters"]
                self.assertEqual(len(encounters), 5)
                for card_id in encounters:
                    self.assertIn(card_id, CardsDB.papers)

    def test_the_scenarios_name_cards_and_sets_that_exist(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                scenario = read("data/scenarios/%s.json" % name)

                for card_id in scenario["villain"] + scenario["encounters"]:
                    self.assertIn(card_id, CardsDB.papers)
                for pair in scenario["schemes"] + scenario["set_aside"]:
                    for card_id in pair.split(","):
                        self.assertIn(card_id, CardsDB.papers)
                for modular in scenario["modular_sets"]:
                    self.assertIn(modular, MODULAR_SETS)
                    self.assertTrue(
                        (ROOT / ("data/encounter_sets/%s.json" % modular)).exists())

                # Expert is the same leader two stages further on.
                self.assertEqual(scenario["expert"], name.endswith("_expert"))
                if scenario["expert"]:
                    self.assertIn("expert", scenario["encounter_sets"])

    def test_the_leaders_come_in_four_stages_each(self):
        stages = {}
        for card_id in LEADERS:
            paper = CardsDB.papers[card_id]
            stages.setdefault(paper.name, []).append(paper.desc["Stage"])
        self.assertEqual(len(stages), 2)
        for name, seen in stages.items():
            with self.subTest(leader=name):
                self.assertEqual(set(seen), {"I", "II", "III", "IV"})

    def test_she_hulk_punishes_the_hero_who_just_flipped_up(self):
        module = load_card("cards.pack.synthezoid.she_hulk.leader")
        abilities = module.SheHulkLeaderAbilities(stage_two=False)
        self.assertEqual(len(abilities), 2)

        effect = Mock()
        message = Mock()
        abilities[1].operation(effect, message)

        this = effect.this.CastTo.return_value
        this.DealDamage.assert_called_once_with([message.trigger], 1, effect)

    def test_she_hulk_stage_two_arrives_rather_than_arms_herself(self):
        module = load_card("cards.pack.synthezoid.she_hulk.leader")
        with patch.object(module.AbilityFactory, "WhenCardSetup") as setup, \
             patch.object(module.AbilityFactory, "WhenThisRevealed") as revealed:
            module.SheHulkLeaderAbilities(stage_two=False)
            setup.assert_called_once()
            revealed.assert_not_called()

            setup.reset_mock()
            module.SheHulkLeaderAbilities(stage_two=True)
            revealed.assert_called_once()
            setup.assert_not_called()

    def test_vision_turns_over_after_the_first_step_of_the_villain_phase(self):
        module = load_card("cards.pack.synthezoid.vision.leader")
        with patch.object(module.AbilityFactory, "AfterResolveVillainPhaseStep") as step:
            module.VisionLeaderAbilities(stage_two=False)
        self.assertEqual(step.call_args.args[1], 1)

        with patch.object(module, "FlipMassForm") as flip:
            step.call_args.args[2](Mock(), Mock())
        flip.assert_called_once()

    def test_density_control_only_spends_itself_on_a_real_flip(self):
        module = load_card("cards.pack.synthezoid.vision.57050")
        with patch.object(module.AbilityFactory, "WhenUnitWouldScheme") as scheme:
            module.GetAbilities()
        to_intangible = scheme.call_args.args[2]

        effect = Mock()
        with (
            patch.object(module, "FlipMassForm", return_value=False) as flip,
            patch.object(module, "Faces") as faces,
        ):
            to_intangible(effect, Mock())
        self.assertEqual(flip.call_args.args[1], module.INTANGIBLE)
        faces.DiscardAll.assert_not_called()

        with (
            patch.object(module, "FlipMassForm", return_value=True),
            patch.object(module, "Faces") as faces,
        ):
            to_intangible(effect, Mock())
        faces.DiscardAll.assert_called_once()

    def test_the_thunderbolts_take_the_cooperative_half(self):
        module = load_card("cards.pack.synthezoid.thunderbolts")
        landed = []
        abilities = module.ThunderboltAbilities(
            lambda player, effect: landed.append("revealed"))

        effect = Mock()
        with patch.object(module.Worlds, "GetYourTeamLeader", return_value=None):
            abilities[0].operation(effect, Mock())
        self.assertEqual(landed, ["revealed"])

    def test_penance_hits_harder_when_he_is_revealed_than_when_boosted(self):
        module = load_card("cards.pack.synthezoid.thunderbolts.57019")
        recorded = []
        with patch.object(module, "ThunderboltAbilities") as factory:
            module.GetAbilities()
        revealed, boosted = factory.call_args.args

        player, effect = Mock(), Mock()
        with patch.object(module.Utility, "DealDamageToCharacterYouControl") as deal:
            revealed(player, effect)
            boosted(player, effect)
            recorded = [call.args[1] for call in deal.call_args_list]
        self.assertEqual(recorded, [2, 1])


if __name__ == "__main__":
    unittest.main()
