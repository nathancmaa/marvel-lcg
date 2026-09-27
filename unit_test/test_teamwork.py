"""Teamwork adds the power the hero actually uses, including ATK against assault."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class TeamworkTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def thwart(self, scheme_name, *, teamwork=True):
        """Thor thwarts ``scheme_name``; Daredevil (01058) is exhausted for Teamwork."""
        from game.world.world_render import WorldRender

        commands = ['Puzzle.ClearHand()']
        if teamwork:
            commands.append('Puzzle.CreateHandCards("06032")')
        commands += [
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.PutIntoPlay("40189")',
            'Puzzle.PutIntoPlay("01058")',
            f'Puzzle.PlaceThreat("{scheme_name}", 4)',
        ]
        seen = {"thwarted": False, "teamwork": False}
        prompts = []

        def choose(prompt):
            prompts.append(prompt.event_name)
            if len(prompts) > 20:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["thwarted"]:
                    return None
                thor = world.GetFirstPlayer().GetIdentity()
                scheme = world.FindCardsOnField(name=scheme_name)[0]
                seen.update(scheme=scheme, before=scheme.threat)
                option = next(option for option in prompt.options
                              if option.get("name") == "Thwart"
                              and option.get("bind_id") == thor.card.object_id)
                seen["thwarted"] = True
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option), [str(scheme.card.object_id)], [])
            if prompt.event_name == "WhenUnitUseBasicPower":
                seen["teamwork"] = True
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(Fixture("rhino", ("thor",), 5, tuple(commands)),
                               HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        self.assertEqual(seen["teamwork"], teamwork)
        daredevil = game.world.FindCardsOnField(name="Daredevil")[0]
        return seen["before"] - seen["scheme"].threat, daredevil

    def test_teamwork_adds_the_allys_atk_against_an_assault_scheme(self):
        alone, _ = self.thwart("Mutant Insurrection", teamwork=False)
        together, daredevil = self.thwart("Mutant Insurrection")

        self.assertTrue(daredevil.IsExhaust())
        self.assertEqual(together - alone, daredevil.attack)

    def test_teamwork_adds_the_allys_thw_against_an_ordinary_scheme(self):
        alone, _ = self.thwart("The Break-In!", teamwork=False)
        together, daredevil = self.thwart("The Break-In!")

        self.assertTrue(daredevil.IsExhaust())
        self.assertEqual(together - alone, daredevil.thwart)


if __name__ == "__main__":
    unittest.main()
