"""Moving players between game areas.

Kang is the only scenario that splits the table across game areas, and the
only one that gathers players back out of them -- which is why a bug here
stayed hidden until someone played it.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401
from engine.lib.random import Random
from engine.lib.version import Ver
from cards.database import CardsDB
from game.scene.loader import SceneLoader
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class GameAreaMoveTests(unittest.TestCase):

    def build_world(self):
        scenario = json.loads(
            (ROOT / 'data/scenarios/rhino.json').read_text(encoding='utf-8'))
        hero = (ROOT / 'deck/starter/spider_man.json').read_text(encoding='utf-8')
        scene = SceneLoader.NewFromJson(
            json.dumps(scenario), None, [hero], 1,
            ['v18_all', 'disable_setup_draw_cards', 'disable_resolve_mulligans'],
            {},
        )
        manager = Mock()
        manager.skip.is_skipping = True
        manager.undo.GetFastUndoHandle.return_value = None
        world = World(scene, [Mock(manager=manager)])
        world.rule.SetRule(scene.rules, scene.is_puzzle, scene.seed)

        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False
        game = Mock()
        game.controller_manager = manager
        game.state.is_running = True
        game.session.version.IsFirstPlayerToken.return_value = True
        Random.SetSeed(1)
        with (
            patch.object(Engine, 'game', game, create=True),
            patch.object(Engine, 'statistics', statistics, create=True),
        ):
            world.Initialize()
        return world

    def test_moving_a_player_into_their_own_area_does_nothing(self):
        """The crash a solo Kang game hits when an aspect is defeated.

        Kang's when-defeated ability gathers the players out of the defeated
        aspect's area into the first one. In a solo game that is frequently the
        area the player is already standing in, and AddPlayer walked their
        cards into AddCard, which asserts a card is not already in the area it
        is being added to -- so every card in the deck tripped it and the game
        ended in a traceback.
        """
        world = self.build_world()
        player = world.players[0]
        here = player.GetGameArea()
        self.assertIs(here, world.GetFirstGameArea())

        before = len(player.player_deck.Get()) + len(player.hand_cards.Get())
        here.AddPlayer(player)
        after = len(player.player_deck.Get()) + len(player.hand_cards.Get())

        self.assertEqual(before, after, 'a no-op move must not disturb the deck')
        self.assertIs(player.GetGameArea(), here)


if __name__ == '__main__':
    unittest.main()
