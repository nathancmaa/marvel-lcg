"""An Alliance cost needs one character of each named trait."""

import unittest

from unit_test.real_game_support import RealGameCase


class AllianceCostTests(RealGameCase):

    def play_combine_forces(self, allies):
        """Combine Forces (48031): exhaust an X-Force and an X-Men character
        -> defeat a non-Elite minion. Returns (offered, allies exhausted,
        Vulture still in play, prompts seen after the play)."""
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("48031", "01088", "01089")',
            'puzzle.ChangeFormFor(0, "Hero")',
            *[f'puzzle.PutIntoPlay("{ally}")' for ally in allies],
            'puzzle.PutIntoPlay("01167")',  # Vulture
        ]
        stage = {"played": False, "offered": False}
        self.cost_prompts = []

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name != "WhenPlayerInTurn":
                if stage["played"]:
                    # Pay the cost with every offered alliance character,
                    # then the minion target.
                    option = prompt.options[0] if prompt.options else None
                    if option and option.get("target_num_range", [0, 0])[1] >= 2:
                        self.cost_prompts.append(option)
                        targets = [
                            t.get("id", t) if isinstance(t, dict) else t
                            for t in option.get("all_legal_targets", [])
                        ][:2]
                        return self.choice(option, targets)
                return self.default(prompt)
            if stage["played"]:
                return None
            card = next(f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "48031")
            option = self.option_for_card(prompt, card)
            stage["played"] = True
            if option is None:
                return None
            stage["offered"] = True
            vulture = world.FindCardsOnField(name="Vulture")[0]
            resources = [e for e in self.payment_effect_ids(option)]
            return self.choice(option, [vulture.card.object_id], resources[-1:])

        game, _ = self.run_game(["spider_man"], setup, choose, seed=470031)
        self.assertNoGameErrors()
        world = game.world
        exhausted = sorted(
            face.paper.card_id for face in world.const_players[0].GetControlAllies()
            if face.paper.card_id in allies and face.IsExhaust()
        )
        return stage["offered"], exhausted, bool(world.FindCardsOnField(name="Vulture"))

    def test_two_x_men_cannot_pay(self):
        offered, exhausted, vulture = self.play_combine_forces(["32002", "32011"])
        self.assertFalse(offered)
        self.assertEqual(exhausted, [])
        self.assertTrue(vulture)

    def test_an_x_force_and_an_x_men_pay(self):
        offered, exhausted, vulture = self.play_combine_forces(["32002", "40014"])
        self.assertTrue(offered)
        self.assertEqual(exhausted, ["32002", "40014"])
        self.assertFalse(vulture)

    def test_cost_prompt_carries_the_alliance_rule(self):
        # Three candidates, so the player is asked which two pay.
        offered, exhausted, vulture = self.play_combine_forces(["32002", "32011", "40014"])
        self.assertTrue(offered)
        self.assertEqual(len(self.cost_prompts), 1)
        option = self.cost_prompts[0]
        self.assertEqual(option.get("select_rule"), "MustIncludeTraits")
        self.assertEqual(sorted(option.get("target_must_include_traits")), ["t_X-FORCE", "t_X-MEN"])

    def cosmic_alliance(self, target_names):
        """Cosmic Alliance (25036): ready an Avenger and a Guardian character."""
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("25036", "01088", "01089", "01090")',
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.PutIntoPlay("01020")',  # Hellcat, Avenger
            'puzzle.PutIntoPlay("01066")',  # Hawkeye, Avenger
            'puzzle.PutIntoPlay("16019")',  # Rocket Raccoon, Guardian
            'puzzle.Exhaust("Hellcat", "Hawkeye", "Rocket Raccoon")',
        ]
        stage = {"played": False}

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name != "WhenPlayerInTurn":
                return self.default(prompt)
            if stage["played"]:
                return None
            stage["played"] = True
            card = next(f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "25036")
            option = self.option_for_card(prompt, card)
            self.assertIsNotNone(option)
            targets = [world.FindCardsOnField(name=name)[0].card.object_id for name in target_names]
            return self.choice(option, targets, self.payment_effect_ids(option)[-3:])

        game, _ = self.run_game(["captain_marvel"], setup, choose, seed=250036)
        world = game.world
        return {
            name: world.FindCardsOnField(name=name)[0].IsExhaust()
            for name in ("Hellcat", "Hawkeye", "Rocket Raccoon")
        }

    def test_cosmic_alliance_rejects_two_avengers(self):
        exhausted = self.cosmic_alliance(["Hellcat", "Hawkeye"])
        self.assertEqual(exhausted, {"Hellcat": True, "Hawkeye": True, "Rocket Raccoon": True})

    def test_cosmic_alliance_readies_an_avenger_and_a_guardian(self):
        exhausted = self.cosmic_alliance(["Hellcat", "Rocket Raccoon"])
        self.assertNoGameErrors()
        self.assertEqual(exhausted, {"Hellcat": False, "Hawkeye": True, "Rocket Raccoon": False})


if __name__ == "__main__":
    unittest.main()
