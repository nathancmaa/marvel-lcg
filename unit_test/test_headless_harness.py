"""The headless driver plays a real game to a prompt, with no mocks."""

import contextlib
import io
import unittest

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database, run_fixture_to_prompt


class HeadlessHarnessTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_a_fresh_game_reaches_the_players_turn(self):
        fixture = Fixture("rhino", ("spider_man",), 424242)
        with contextlib.redirect_stdout(io.StringIO()):
            game, devices = run_fixture_to_prompt(fixture)

        self.assertIn("WhenPlayerInTurn", devices.stopped_prompt.event_name)
        self.assertTrue(devices.stopped_prompt.options)
        identity = game.world.GetFirstPlayer().GetIdentity()
        self.assertEqual(identity.paper.card_id[:5], "01001")

    def test_puzzle_commands_place_exact_cards(self):
        fixture = Fixture(
            "rhino",
            ("spider_man",),
            424243,
            ('Puzzle.ClearHand()', 'Puzzle.CreateHandCards("01002")'),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            game, _ = run_fixture_to_prompt(fixture)

        hand = [face.paper.card_id for face in game.world.GetFirstPlayer().hand_cards.Get()]
        self.assertEqual(hand, ["01002"])


if __name__ == "__main__":
    unittest.main()
