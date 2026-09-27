"""Crisis of Faith (48026) discards Attack and Defense events, either kind."""

import unittest

from unit_test.real_game_support import RealGameCase


class CrisisOfFaithTests(RealGameCase):

    def resolve(self, hand):
        setup = [
            'puzzle.ClearHand()',
            f'puzzle.CreateHandCards({", ".join(repr(card) for card in hand)})',
            'puzzle.Reveal("48026")',
        ]
        offered = []

        def choose(prompt):
            if prompt.event_name == "WhenPlayerInTurn":
                return None
            for option in prompt.options:
                if "Discard_each" in str(option):
                    offered.append(option.get("target_num_range"))
                    targets = [
                        t.get("id", t) if isinstance(t, dict) else t
                        for t in option.get("all_legal_targets", [])
                    ]
                    return self.choice(option, targets)
            return self.default(prompt)

        game, _ = self.run_game(["nightcrawler"], setup, choose, seed=48026)
        self.assertNoGameErrors()
        world = game.world
        return (
            offered,
            sorted(face.paper.card_id for face in world.const_players[0].hand_cards.Get()),
            [face.paper.card_id for face in world.FindCardsOnField(name="Crisis of Faith")],
        )

    def test_only_attack_events_are_discarded(self):
        offered, hand, in_play = self.resolve(["48007", "01054", "01088"])
        self.assertEqual(len(offered), 1)
        self.assertEqual(hand, ["01088"])
        self.assertEqual(in_play, [])

    def test_choice_is_available_with_no_attack_or_defense_event(self):
        offered, hand, in_play = self.resolve(["01088", "01089"])
        self.assertEqual(len(offered), 1)
        self.assertEqual(hand, ["01088", "01089"])
        self.assertEqual(in_play, [])


if __name__ == "__main__":
    unittest.main()
