"""A player card that says "the villain" lets you choose among several."""

import unittest

from unit_test.real_game_support import RealGameCase


class ChooseVillainTests(RealGameCase):

    def creole_charmer(self, scenario, heroes, pick_last):
        """Creole Charmer (37009): remove 3 threat; if that clears the
        scheme, confuse the villain."""
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("37009", "01088", "01089")',
            'puzzle.SetThreat(world.area_schemes_main.Get()[0], 2)',
        ]
        stage = {"played": False}
        asked = []

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                if stage["played"]:
                    return None
                stage["played"] = True
                card = next(f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "37009")
                option = self.option_for_card(prompt, card)
                self.assertIsNotNone(option)
                scheme = world.area_schemes_main.Get()[0]
                return self.choice(option, [scheme.card.object_id], self.payment_effect_ids(option)[-2:])
            villain_ids = {v.card.object_id for v in world.scenario.area_villain.Get()}
            for option in prompt.options:
                legal = option.get("all_legal_targets", [])
                if len(legal) > 1 and set(legal) <= villain_ids:
                    chosen = legal[-1] if pick_last else legal[0]
                    asked.append((sorted(legal), chosen))
                    return self.choice(option, [chosen])
            return self.default(prompt)

        game, _ = self.run_game(heroes, setup, choose, scenario=scenario, seed=370009)
        self.assertNoGameErrors()
        world = game.world
        return asked, {v.card.object_id: v.IsConfused() for v in world.scenario.area_villain.Get()}

    def test_tower_defense_player_chooses_the_villain(self):
        for pick_last in (False, True):
            with self.subTest(pick_last=pick_last):
                asked, confused = self.creole_charmer("the_tower_defense", ["gambit"], pick_last)
                self.assertEqual(len(asked), 1)
                legal, chosen = asked[0]
                self.assertEqual(len(legal), 2)
                self.assertEqual(confused, {vid: vid == chosen for vid in confused})

    def test_single_villain_is_not_asked(self):
        asked, confused = self.creole_charmer("rhino", ["gambit"], False)
        self.assertEqual(asked, [])
        self.assertEqual(list(confused.values()), [True])

    def test_sinister_six_uses_its_active_villain(self):
        # Sinister Six's scheme defines "the villain" as the active one.
        asked, confused = self.creole_charmer("sinister_six", ["gambit"], False)
        self.assertEqual(asked, [])
        self.assertEqual(sum(confused.values()), 1)

    def test_wrecking_crew_uses_its_active_villain(self):
        asked, confused = self.creole_charmer("the_wrecking_crew", ["gambit"], False)
        self.assertEqual(asked, [])
        self.assertEqual(sum(confused.values()), 1)

    def test_four_horsemen_player_chooses_the_villain(self):
        asked, confused = self.creole_charmer("four_horsemen", ["gambit"], True)
        self.assertEqual(len(asked), 1)
        legal, chosen = asked[0]
        self.assertEqual(len(legal), 4)
        self.assertEqual(confused, {vid: vid == chosen for vid in confused})


class FlashFreezeTests(RealGameCase):

    def test_only_the_attacking_villain_gets_minus_three_attack(self):
        # Flash Freeze (36012) against Proxima Midnight's attack must not
        # weaken Corvus Glaive when he attacks later this phase.
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("36012", "01088")',
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.DoAttack("Proxima Midnight")',
            'puzzle.DoAttack("Corvus Glaive")',
        ]
        seen = {"played": False, "attacks": []}

        def choose(prompt):
            from engine import Engine
            from game.scene.replay.operation import CommandDescriptor
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            if prompt.event_name == "WhenUnitBeingAttack":
                attack = {v.name: v.attack for v in world.scenario.area_villain.Get()}
                seen["attacks"].append((attack, world.const_players[0].GetIdentity().health))
            card = next((f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "36012"), None)
            option = card and self.option_for_card(prompt, card)
            if option and not seen["played"]:
                seen["played"] = True
                return self.choice(option, None, self.payment_effect_ids(option)[-1:])
            return CommandDescriptor() if prompt.show_cancel else self.default(prompt)

        game, _ = self.run_game(["storm"], setup, choose, scenario="the_tower_defense", seed=360012)
        self.assertNoGameErrors()
        self.assertTrue(seen["played"])
        (proxima_attack, _), (corvus_attack, health_before_corvus) = seen["attacks"]
        self.assertEqual(proxima_attack["Proxima Midnight"], 0)
        self.assertEqual(corvus_attack["Corvus Glaive"], 1)
        hero = game.world.const_players[0].GetIdentity()
        self.assertLess(hero.health, health_before_corvus)


if __name__ == "__main__":
    unittest.main()
