"""The Bifrost shuffles the deck after finding and playing an [[Asgard]] ally."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.deck.deck import Deck2
from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


class BifrostTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_deck_is_shuffled_once_after_the_ally_is_played(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", ("valkyrie",), 5, (
            'Puzzle.ClearHand()',
            'Puzzle.CreatePlayerDeck("18011")',
            'Puzzle.PutIntoPlay("25023")',
        ))
        seen = {"activated": False}
        shuffles = []
        prompts = []
        original_shuffle = Deck2.Shuffle

        def shuffle(deck, effect, *args, **kwargs):
            if effect.this.paper.card_id == "25023":
                player = effect.GetInitiator()
                shuffles.append((deck is player.player_deck,
                                 [face.paper.card_id for face in player.allies.Get()]))
            return original_shuffle(deck, effect, *args, **kwargs)

        def choose(prompt):
            prompts.append(prompt.event_name)
            if len(prompts) > 20:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["activated"]:
                    return None
                bifrost = world.FindCardsOnField(name="The Bifrost")[0]
                option = next(option for option in prompt.options
                              if option.get("bind_id") == bifrost.card.object_id)
                seen["activated"] = True
                return CommandDescriptor(HeadlessDeviceManager._DescriptorId(option), [], [])
            for option in prompt.options:
                for target in option.get("all_legal_targets", []):
                    bound = world.object_manager.card_dict.get(int(target))
                    if bound and bound.face.paper.card_id == "18011":
                        return CommandDescriptor(
                            HeadlessDeviceManager._DescriptorId(option), [str(target)], [])
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(Deck2, "Shuffle", new=shuffle), \
            patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game = run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0)
        player = game.world.GetFirstPlayer()
        self.assertIn("18011", [face.paper.card_id for face in player.allies.Get()])
        self.assertEqual(shuffles, [(True, ["18011"])])


if __name__ == "__main__":
    unittest.main()
