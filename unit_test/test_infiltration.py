"""Infiltration (51015) resolves when the encounter deck runs out mid-discard."""

import unittest

from unit_test.real_game_support import RealGameCase


class InfiltrationTests(RealGameCase):

    def play_infiltration(self, declared, deck_cards):
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("51015", "01088", "01089")',
            'puzzle.ChangeFormFor(0, "Hero")',
            f'puzzle.CreateEncounterDeck({", ".join(repr(card) for card in deck_cards)})',
            # Leave only the created cards (emptying the deck would reset it).
            f'Faces.RemoveAllFromGame(Worlds.GetAllVillains(world)[0].encounter_deck.Get()[:-{len(deck_cards)}], DebugRule(hero))',
            'puzzle.SetThreat(world.area_schemes_main.Get()[0], 6)',
        ]
        stage = {"played": False}
        info = {}

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                if stage["played"]:
                    return None
                stage["played"] = True
                card = next(f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "51015")
                option = self.option_for_card(prompt, card)
                self.assertIsNotNone(option)
                scheme = world.area_schemes_main.Get()[0]
                info["threat_before"] = scheme.threat
                return self.choice(option, [scheme.card.object_id], self.payment_effect_ids(option)[-1:])
            numbers = [o for o in prompt.options if str(o.get("name", "")) == str(declared)]
            if numbers:
                return self.choice(numbers[0])
            return self.default(prompt)

        game, devices = self.run_game(["spider_man"], setup, choose, seed=510015)
        self.assertNoGameErrors()
        world = game.world
        scheme = world.area_schemes_main.Get()[0]
        in_hand = [f.paper.card_id for f in world.const_players[0].hand_cards.Get()]
        return info["threat_before"] - scheme.threat, in_hand, bool(world.FindCardsOnField(name="Vulture")), devices

    def test_deck_reset_fulfils_the_discard(self):
        removed, hand, vulture, _ = self.play_infiltration(5, ["01104", "01167"])
        self.assertNotIn("51015", hand)
        self.assertEqual(removed, 2)
        self.assertTrue(vulture)

    def test_full_discard_without_reset(self):
        removed, hand, vulture, _ = self.play_infiltration(2, ["01104", "01105", "01106", "01167"])
        self.assertNotIn("51015", hand)
        self.assertEqual(removed, 2)


if __name__ == "__main__":
    unittest.main()
