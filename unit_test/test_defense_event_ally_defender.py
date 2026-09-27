"""A defense-labelled event keeps an ally that already defends."""

import unittest

from unit_test.real_game_support import RealGameCase

from game.scene.replay.operation import CommandDescriptor


class DefenseEventAllyDefenderTests(RealGameCase):

    def villain_attack(self, play_defiance):
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("26018", "01088", "01089", "01090")',
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.PutIntoPlay("01020")',  # Hellcat
            'puzzle.Flip("26002a")',        # Dense: Intangible cannot defend
        ]
        seen = {"defended": False, "defiance": False, "turns": 0}

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                # End the turn once, so Rhino attacks in the villain phase
                # with a boost card; stop at the next turn.
                seen["turns"] += 1
                return CommandDescriptor() if seen["turns"] == 1 else None
            hellcat = world.FindCardsOnField(name="Hellcat")
            if prompt.event_name == "WhenUnitBeingAttack" and not seen["defended"] and hellcat:
                option = self.option_for_card(prompt, hellcat[0])
                if option:
                    seen["defended"] = True
                    return self.choice(option)
            if prompt.event_name == "WhenBoostCardWouldTurnedFaceUp" and play_defiance and not seen["defiance"]:
                card = next((f for f in world.const_players[0].hand_cards.Get() if f.paper.card_id == "26018"), None)
                option = card and self.option_for_card(prompt, card)
                if option:
                    seen["defiance"] = True
                    return self.choice(option, None, self.payment_effect_ids(option)[-1:])
            return CommandDescriptor() if prompt.show_cancel else self.default(prompt)

        game, devices = self.run_game(["vision"], setup, choose, seed=260018)
        self.assertNoGameErrors()
        self.assertTrue(seen["defended"], [(p.event_name, p.options) for p in devices.prompts][-6:])
        self.assertEqual(seen["defiance"], play_defiance, [(p.event_name, [o.get("name") for o in p.options]) for p in devices.prompts][-8:])
        world = game.world
        vision = world.GetFirstPlayer().GetIdentity()
        hellcat = world.FindCardsOnField(name="Hellcat")
        return vision.health, vision.max_health, hellcat

    def test_defiance_keeps_the_ally_defender(self):
        health, max_health, hellcat = self.villain_attack(True)
        self.assertEqual(health, max_health)
        self.assertTrue(not hellcat or hellcat[0].health < hellcat[0].max_health)

    def test_ally_defends_without_defiance(self):
        health, max_health, hellcat = self.villain_attack(False)
        self.assertEqual(health, max_health)


if __name__ == "__main__":
    unittest.main()
