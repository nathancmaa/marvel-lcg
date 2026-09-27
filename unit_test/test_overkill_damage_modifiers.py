"""A unit that "takes +1 damage" takes it from overkill excess too."""

import unittest

from unit_test.real_game_support import RealGameCase


RESOURCE_CARDS = ("01088", "01089", "01090")


class OverkillTakesExtraDamageTests(RealGameCase):

    def hammer_throw_overkill(self, with_exploit_weakness):
        """Thor's Hammer Throw (8 damage, Overkill) at Vulture (4 health)."""
        setup = [
            'puzzle.ClearHand()',
            'puzzle.CreateHandCards("06005", "33005", "01088", "01089", "01090", "01090")',
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.PutIntoPlay("06009")',  # Mjolnir
            'puzzle.PutIntoPlay("01167")',  # Vulture
        ]
        stage = {"exploit": not with_exploit_weakness, "throw": False}
        info = {}

        def resource_ids(world, option, count):
            hand = world.const_players[0].hand_cards.Get()
            owners = {str(effect.object_id): face.paper.card_id for face in hand for effect in face.effect.GetAll()}
            return [e for e in self.payment_effect_ids(option) if owners.get(e) in RESOURCE_CARDS][:count]

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name in ("WhenUnitBeingAttack", "AfterMinionEngagePlayer"):
                return self.choice(prompt.options[0]) if not prompt.show_cancel else self.default(prompt)
            if prompt.event_name != "WhenPlayerInTurn":
                return self.default(prompt)
            hand = world.const_players[0].hand_cards.Get()
            rhino = world.FindCardsOnField(name="Rhino")[0]
            if not stage["exploit"]:
                stage["exploit"] = True
                card = next(f for f in hand if f.paper.card_id == "33005")
                option = self.option_for_card(prompt, card)
                return self.choice(option, [rhino.card.object_id], resource_ids(world, option, 1))
            if not stage["throw"]:
                stage["throw"] = True
                vulture = world.FindCardsOnField(name="Vulture")[0]
                info["rhino_before"] = rhino.health
                info["vulture_health"] = vulture.health
                card = next(f for f in hand if f.paper.card_id == "06005")
                option = self.option_for_card(prompt, card)
                return self.choice(option, [vulture.card.object_id], resource_ids(world, option, 2))
            return None

        game, _ = self.run_game(["thor"], setup, choose, seed=180011)
        self.assertNoGameErrors()
        world = game.world
        rhino = world.FindCardsOnField(name="Rhino")[0]
        self.assertEqual(world.FindCardsOnField(name="Vulture"), [])
        exploit = world.FindCardsOnField(name="Exploit Weakness")
        self.assertEqual(len(exploit), 1 if with_exploit_weakness else 0)
        return info["rhino_before"] - rhino.health, info["vulture_health"]

    def test_overkill_without_modifier(self):
        dealt, vulture_health = self.hammer_throw_overkill(False)
        self.assertEqual(vulture_health, 4)
        self.assertEqual(dealt, 8 - vulture_health)

    def test_exploit_weakness_adds_to_overkill_damage(self):
        dealt, vulture_health = self.hammer_throw_overkill(True)
        self.assertEqual(vulture_health, 4)
        self.assertEqual(dealt, 8 - vulture_health + 1)


if __name__ == "__main__":
    unittest.main()
