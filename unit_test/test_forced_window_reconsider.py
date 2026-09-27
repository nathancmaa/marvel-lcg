"""A forced ability that becomes legal while its window resolves still resolves.

Two Forced Responses trigger on the same form change. The second is legal
only after the first has resolved. Both are registered on the villain in a
real game, then the hero changes form through the debug console.
"""

import unittest

from unit_test.real_game_support import RealGameCase


class ForcedWindowReconsiderTests(RealGameCase):

    def test_second_forced_response_resolves_after_the_first_enables_it(self):
        resolved = []

        def register_and_change_form(prompt):
            from engine import Engine
            from game.ability import Ability, AbilityType
            from game.message import Message
            villain = Engine.game.world.scenario.area_villain.Get()[0]
            villain.effect.RegisterTemp(
                Ability(
                    AbilityType.ForcedResponse,
                    Message.AfterUnitChangeForm,
                    [lambda effect, message: "first" not in resolved],
                    lambda effect, message: resolved.append("first"),
                ),
                Ability(
                    AbilityType.ForcedResponse,
                    Message.AfterUnitChangeForm,
                    [lambda effect, message: resolved == ["first"]],
                    lambda effect, message: resolved.append("second"),
                ),
                unregister_after_exec=False,
                until_round_end=True,
            )
            return self.debug('puzzle.ChangeFormFor(0, "Hero")')

        stage = {"turns": 0}

        def choose(prompt):
            if prompt.event_name == "WhenPlayerInTurn":
                stage["turns"] += 1
                if stage["turns"] == 1:
                    return register_and_change_form(prompt)
                return None
            return self.default(prompt)

        game, _ = self.run_game(["spider_man"], [], choose, seed=387)
        self.assertNoGameErrors()
        self.assertEqual(resolved, ["first", "second"])


if __name__ == "__main__":
    unittest.main()
