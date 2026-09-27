"""Dynamic Duo shuffles the deck once, after both cards are in hand."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order
from game.deck.deck import Deck2
from game.scene import SceneLoader
from game.scene.replay.operation import CommandDescriptor
from game.test.headless import HeadlessDeviceManager
from game.test.harness import initialize_database, run_scene_with_devices
from game.world.world_render import WorldRender


class TestDynamicDuo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def play_dynamic_duo(self, setup_commands):
        scene = SceneLoader.NewScene("rhino", None, ["iron_man"], 100)
        scene.rules = ["v18_all"]
        commands = [
            'Gain("Dynamic Duo")',
            'Discard("Two Against the World", "War Machine")',
            *setup_commands,
            'Play("Dynamic Duo")',
        ]
        command_index = 0

        def choose(prompt):
            nonlocal command_index
            if prompt.event_name == "WhenPlayerInTurn":
                if command_index == len(commands):
                    return None
                command = commands[command_index]
                command_index += 1
                Engine.game.controller_manager.console.SetCommand(
                    command, Engine.game.world,
                )
                return CommandDescriptor()
            return HeadlessDeviceManager._DefaultChoice(prompt)

        devices = HeadlessDeviceManager(choice_provider=choose)
        shuffles = []
        original_shuffle = Deck2.Shuffle

        def shuffle(deck, effect, *args, **kwargs):
            if effect.this.paper.card_id == "62022":
                player = effect.GetInitiator()
                shuffles.append((
                    deck,
                    {face.name for face in player.hand_cards.Get()},
                ))
            return original_shuffle(deck, effect, *args, **kwargs)

        with contextlib.redirect_stdout(io.StringIO()), patch.object(
            Deck2, "Shuffle", new=shuffle,
        ), patch.object(WorldRender, "ErrorOccurred") as error:
            game = run_scene_with_devices(scene, devices)

        error.assert_not_called()
        self.assertEqual(command_index, len(commands))
        self.assertIsNotNone(devices.stopped_prompt)
        self.assertEqual(devices.stopped_prompt.event_name, "WhenPlayerInTurn")
        return game.world.const_players[0], shuffles

    @staticmethod
    def move_to_deck(name):
        return (
            f'Faces.MoveAllTo([p.discard_pile.FindCard(name="{name}")], '
            'p.player_deck, DebugRule(hero))'
        )

    def assert_shuffled_after_adding(self, player, shuffles, expected_names):
        self.assertEqual(len(shuffles), 1)
        deck, hand_at_shuffle = shuffles[0]
        self.assertIs(deck, player.player_deck)
        self.assertTrue(expected_names.issubset(hand_at_shuffle))
        hand = {face.name for face in player.hand_cards.Get()}
        self.assertTrue(expected_names.issubset(hand))

    def test_shuffles_once_after_retrieving_cards_from_each_source_combination(self):
        for team_up_in_deck in (False, True):
            for ally_in_deck in (False, True):
                with self.subTest(team_up_in_deck=team_up_in_deck, ally_in_deck=ally_in_deck):
                    setup = []
                    if team_up_in_deck:
                        setup.append(self.move_to_deck("Two Against the World"))
                    if ally_in_deck:
                        setup.append(self.move_to_deck("War Machine"))
                    player, shuffles = self.play_dynamic_duo(setup)

                    self.assert_shuffled_after_adding(
                        player, shuffles, {"Two Against the World", "War Machine"},
                    )
                    for name in ("Two Against the World", "War Machine"):
                        self.assertIsNone(player.player_deck.FindCard(name=name))
                        self.assertIsNone(player.discard_pile.FindCard(name=name))

    def test_missing_ally_still_adds_team_up_and_shuffles(self):
        player, shuffles = self.play_dynamic_duo(['Remove("War Machine")'])

        self.assert_shuffled_after_adding(player, shuffles, {"Two Against the World"})
        self.assertIsNone(player.hand_cards.FindCard(name="War Machine"))

    def test_missing_team_up_still_shuffles_without_retrieving_an_ally(self):
        player, shuffles = self.play_dynamic_duo(['Remove("Two Against the World")'])

        self.assert_shuffled_after_adding(player, shuffles, set())
        self.assertIsNone(player.hand_cards.FindCard(name="Two Against the World"))
        self.assertIsNone(player.hand_cards.FindCard(name="War Machine"))
        self.assertIsNotNone(player.discard_pile.FindCard(name="War Machine"))


if __name__ == "__main__":
    unittest.main()
