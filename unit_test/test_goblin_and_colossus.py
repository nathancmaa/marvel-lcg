"""Goblin takes damage only from [physical] cards; Colossus's setup searches the deck."""

import contextlib
import importlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class GoblinDamageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_goblin_ignores_retaliate_but_takes_physical_card_damage(self):
        # Black Panther's Retaliate hits the attacking Goblin; the identity
        # has no printed resource, so Goblin survives. Daredevil (a
        # [physical] ally) then defeats it.
        fixture = Fixture("rhino", ("black_panther",), 390430, (
            'Puzzle.ChangeFormFor(0, "Hero")',
            'Puzzle.PutIntoPlay("01058")',
            'Puzzle.CreateEncounterDeck("39043", "01188")',
            'Puzzle.Reveal("39043")',
            'Puzzle.DoAttack("Goblin")',
        ))
        state = {"attacked": False, "health_after_retaliate": None}

        def choose(prompt):
            if prompt.event_name == "WhenUnitBeingAttack":
                return CommandDescriptor()  # Black Panther does not defend.
            if prompt.event_name == "WhenPlayerInTurn" and not state["attacked"]:
                world = Engine.game.world
                goblin = world.FindCardsOnField(name="Goblin")[0]
                daredevil = world.FindCardsOnField(name="Daredevil")[0]
                state["health_after_retaliate"] = goblin.health
                option = next(
                    option for option in prompt.options
                    if option.get("name") == "Attack"
                    and option.get("bind_id") == daredevil.card.object_id
                )
                state["attacked"] = True
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option),
                    [str(goblin.card.object_id)],
                    [],
                )
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            return HeadlessDeviceManager._DefaultChoice(prompt)

        from game.world.world_render import WorldRender
        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        self.assertEqual(state["health_after_retaliate"], 1)
        self.assertTrue(state["attacked"])
        self.assertEqual(game.world.FindCardsOnField(name="Goblin"), [])
        self.assertIn(
            "39043",
            [face.paper.card_id for face in game.world.scenario.encounter_discard_pile.Get()],
        )


class _Identity:
    def CastTo(self, _card_type):
        return self


class _Effect:
    def __init__(self) -> None:
        self.this = _Identity()
        self.initiator = object()

    def GetInitiator(self):
        return self.initiator


class ColossusSetupTests(unittest.TestCase):

    def test_organic_steel_is_searched_for_in_the_deck_only(self):
        module = importlib.import_module("cards.pack.mut_gen.colossus.32001b")
        setup_ability = module.GetAbilities()[0]
        effect = _Effect()

        with patch.object(module.Search, "PlayerCard", return_value=None) as search:
            setup_ability.operation(effect, object())

        self.assertTrue(search.call_args.kwargs["include_player_deck"])
        self.assertFalse(search.call_args.kwargs.get("include_discard_pile", False))
        self.assertEqual(search.call_args.kwargs["name"], "Organic Steel")


if __name__ == "__main__":
    unittest.main()
