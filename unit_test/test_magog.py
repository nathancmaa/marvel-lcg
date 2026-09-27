"""MaGog: one random MojoMania modular set, and Crime Scene Investigation
does not block Melee in the Mojo-seum's completion reset."""

import contextlib
import io
import json
import unittest
from importlib import import_module
from pathlib import Path
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database, run_fixture_to_prompt


ROOT = Path(__file__).resolve().parents[1]
MOJOMANIA_MODULAR_SETS = ["crime", "fantasy", "horror", "sci_fi", "sitcom", "western"]


class MagogModularSetTests(unittest.TestCase):

    def test_scenarios_offer_every_mojomania_modular_set(self):
        for filename in ("magog.json", "magog_expert.json"):
            with self.subTest(scenario=filename):
                scenario = json.loads((ROOT / "data" / "scenarios" / filename).read_text(encoding="utf-8"))
                self.assertEqual(scenario["modular_sets"], MOJOMANIA_MODULAR_SETS)

    def select_random_modular_set(self):
        module = import_module("cards.pack.mojo.magog.39002a")
        return module, module.GetAbilities()[0]

    def test_setup_keeps_one_random_modular_set(self):
        module, ability = self.select_random_modular_set()
        effect = Mock()
        message = Mock()
        message.encounter_set_names = ["standard", "expert", *MOJOMANIA_MODULAR_SETS]

        with patch.object(module.Rand, "RandomChoice2", return_value=["horror"]) as choose:
            ability.operation(effect, message)

        choose.assert_called_once_with(MOJOMANIA_MODULAR_SETS, 1, effect)
        self.assertEqual(message.encounter_set_names, ["standard", "expert", "horror"])

    def test_a_single_modular_set_is_kept_without_a_random_draw(self):
        module, ability = self.select_random_modular_set()
        message = Mock()
        message.encounter_set_names = ["standard", "crime"]

        with patch.object(module.Rand, "RandomChoice2") as choose:
            ability.operation(Mock(), message)

        choose.assert_not_called()
        self.assertEqual(message.encounter_set_names, ["standard", "crime"])


class CrimeSceneInvestigationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_melee_in_the_mojo_seum_still_resets_its_threat(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("magog", ("spider_man",), 5, (
            'Puzzle.PutIntoPlay("39037")',
            'Puzzle.PlaceThreat("Melee in the Mojo-seum", 20)',
        ))
        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game, _ = run_fixture_to_prompt(fixture)

        self.assertEqual(error.call_count, 0)
        world = game.world
        main_scheme = world.area_schemes_main.Get()[0]
        crime_scene = next(face for face in world.area_schemes_side.Get()
                           if face.paper.card_id == "39037")
        champion = next(face for face in world.area_environment.Get()
                        if face.name == "The Champion")
        self.assertEqual(main_scheme.threat, 0)
        self.assertEqual(champion.GetCounters("ratings"), 2)
        # Crime Scene still protects its own threat.
        self.assertGreater(crime_scene.threat, 0)


if __name__ == "__main__":
    unittest.main()
