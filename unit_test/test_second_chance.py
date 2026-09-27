"""Second Chance shuffles back every identity-specific card, whatever its set."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class SecondChanceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_pym_particles_is_shuffled_back_for_wasp(self):
        from game.world.world_render import WorldRender

        # Wasp's Pym Particles (13007) reprints Ant-Man's, so its set name is
        # Ant-Man's, not Wasp's; it is still identity-specific.
        fixture = Fixture("rhino", ("wasp",), 5, (
            'Puzzle.CreatePlayerDiscardPile("13007", "13003")',
            'Puzzle.PutIntoPlay("61028")',
            'Puzzle.PlaceThreat("Second Chance", -10)',
        ))
        seen = {}

        def choose(prompt):
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            shuffle = next((option for option in prompt.options
                            if str(option.get("name", "")).startswith("Shuffle_all_identity")), None)
            if shuffle is not None:
                player = Engine.game.world.GetFirstPlayer()
                seen["cards"] = [face for face in player.discard_pile.Get()
                                 if face.paper.card_id in ("13007", "13003")]
                return CommandDescriptor(HeadlessDeviceManager._DescriptorId(shuffle), [], [])
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        player = game.world.GetFirstPlayer()
        self.assertEqual(sorted(face.paper.card_id for face in seen["cards"]), ["13003", "13007"])
        for face in seen["cards"]:
            self.assertIn(face, player.player_deck.Get())


if __name__ == "__main__":
    unittest.main()
