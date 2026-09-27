"""Nebula II/III: only the first Technique revealed each round gains surge."""

import unittest

from unit_test.real_game_support import RealGameCase


class NebulaTechniqueSurgeTests(RealGameCase):

    def test_second_players_technique_does_not_surge(self):
        setup = [
            # Evasive Maneuvering for the first player, Wide Stance for the second.
            'puzzle.FindOrCreateFace("16095").Reveal(p0, DebugRule(hero))',
            'puzzle.FindOrCreateFace("16098").Reveal(p1, DebugRule(hero))',
        ]

        def choose(prompt):
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            return self.default(prompt)

        game, _ = self.run_game(
            ["spider_man", "captain_marvel"], setup, choose,
            scenario="nebula_expert", seed=160089,
        )
        self.assertNoGameErrors()
        world = game.world
        self.assertIn(world.FindCardsOnField(name="Nebula")[0].paper.card_id, ("16089", "16090"))
        self.assertTrue(world.FindCardsOnField(name="Evasive Maneuvering"))
        self.assertTrue(world.FindCardsOnField(name="Wide Stance"))
        # Surge deals a facedown encounter card: the first player's Technique
        # surges, the second player's does not.
        dealt = [player.dealt_encounter_cards.GetSize() for player in world.const_seat_order_players]
        self.assertEqual(dealt, [1, 0])


if __name__ == "__main__":
    unittest.main()
