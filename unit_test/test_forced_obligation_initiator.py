"""A given obligation's forced ability resolves for the player who holds it."""

import unittest

from unit_test.real_game_support import RealGameCase


class ProtectHumanityTests(RealGameCase):

    def test_villain_attack_is_redirected_to_a_chosen_ally(self):
        setup = [
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.PutIntoPlay("01020")',  # Hellcat
            'puzzle.Reveal("59004")',       # Protect Humanity: puts Amadeus Cho into play
            'puzzle.DoAttack("Rhino")',
        ]
        redirect_prompts = []

        def choose(prompt):
            from engine import Engine
            world = Engine.game.world
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            if prompt.event_name == "WhenUnitWouldAttackUnit":
                option = prompt.options[0]
                redirect_prompts.append(sorted(option.get("all_legal_targets", [])))
                hellcat = world.FindCardsOnField(name="Hellcat")[0]
                return self.choice(option, [hellcat.card.object_id])
            return CommandDescriptorOrDefault(self, prompt)

        game, devices = self.run_game(["hercules"], setup, choose, seed=59004)
        self.assertNoGameErrors()
        world = game.world
        self.assertEqual(len(redirect_prompts), 1)
        self.assertEqual(len(redirect_prompts[0]), 2)  # Hellcat and Amadeus Cho
        hercules = world.GetFirstPlayer().GetIdentity()
        self.assertEqual(hercules.health, hercules.max_health)
        hellcat = world.FindCardsOnField(name="Hellcat")
        self.assertTrue(not hellcat or hellcat[0].health < hellcat[0].max_health)


def CommandDescriptorOrDefault(case, prompt):
    # Decline optional responses (e.g. defending); take the default otherwise.
    from game.scene.replay.operation import CommandDescriptor
    return CommandDescriptor() if prompt.show_cancel else case.default(prompt)


if __name__ == "__main__":
    unittest.main()
