"""Pacifism and Lost Visor stop their hero attacking in any way, in either form."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database, run_fixture_to_prompt


class CannotAttackObligationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def turn_options(self, hero, commands):
        from game.world.world_render import WorldRender

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game, devices = run_fixture_to_prompt(Fixture("rhino", (hero,), 5, commands))
        self.assertEqual(error.call_count, 0)
        return game, devices.stopped_prompt.options

    def test_pacifism_blocks_attack_events(self):
        game, options = self.turn_options("wonder_man", (
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("58004", "01088", "01088")',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.Reveal("58025")',
        ))
        player = game.world.GetFirstPlayer()
        ionic_blast = next(face for face in player.hand_cards.Get() if face.paper.card_id == "58004")

        self.assertTrue(player.IsHero())
        self.assertEqual([face.paper.card_id for face in player.obligations_area.Get()], ["58025"])
        self.assertFalse([option for option in options
                          if option.get("bind_id") == ionic_blast.card.object_id])
        self.assertNotIn("Attack", [option.get("name") for option in options])

    def test_lost_visor_stops_cyclops_attacking(self):
        game, options = self.turn_options("cyclops", (
            'Puzzle.ClearHand()',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.Reveal("33027")',
        ))
        player = game.world.GetFirstPlayer()

        self.assertTrue(player.IsHero())
        self.assertEqual([face.paper.card_id for face in player.obligations_area.Get()], ["33027"])
        self.assertNotIn("Attack", [option.get("name") for option in options])


if __name__ == "__main__":
    unittest.main()
