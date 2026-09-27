"""Cards that remove "a total of N threat from among schemes" remove all N.

Each test plays the card in a real game with the main scheme at 4 threat
and Breakin' & Takin' (01107) at 2, and checks the target prompt and where
the threat came off.
"""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, initialize_database, run_fixture
from game.test.headless import HeadlessDeviceManager


def payment_effect_ids(option):
    effects = []
    for payment in option.get("target_payment", {}).values():
        for entry in payment.get("payment", []):
            effects.extend(str(effect_id) for effect_id in entry)
    return effects


class DistributedThreatRemovalTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def play(self, hero, card_id, pick_targets, *, extra=(), on_prompt=None):
        """Play ``card_id``; ``pick_targets(option, main, side)`` returns target ids,
        or is None for the play option's default targets."""
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", (hero,), 5, (
            'Puzzle.ClearHand()',
            f'Puzzle.CreateHandCards("{card_id}", "01088", "01088", "01088")',
            'Puzzle.ChangeFormFor(0,"Identity")',
            'Puzzle.PlaceThreat("The Break-In!", 4)',
            'Puzzle.PutIntoPlay("01107")',
            *extra,
        ))
        seen = {"played": False, "ranges": []}
        prompts = []

        def targets_for(option, world):
            main = world.area_schemes_main.Get()[0]
            side = world.FindCardsOnField(name="Breakin' & Takin'")[0]
            seen.update(main=main, side=side)
            seen["ranges"].append(list(option.get("target_num_range")))
            seen["legal"] = sorted(set(int(target) for target in option.get("all_legal_targets", [])))
            if pick_targets is None:
                return []
            return [str(target) for target in pick_targets(option, main.card.object_id, side.card.object_id)]

        def choose(prompt):
            prompts.append(prompt.event_name)
            if len(prompts) > 30:
                raise AssertionError(f"Unexpected repeated prompt: {prompts[-3:]}")
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if prompt.event_name == "WhenPlayerInTurn":
                if seen["played"]:
                    return None
                card = next(face for face in player.hand_cards.Get() if face.paper.card_id == card_id)
                option = next(option for option in prompt.options
                              if option.get("bind_id") == card.card.object_id)
                seen["played"] = True
                seen["before"] = (world.area_schemes_main.Get()[0].threat,
                                  world.FindCardsOnField(name="Breakin' & Takin'")[0].threat)
                if pick_targets is None:
                    minimum = int(option.get("target_num_range", [0, 0])[0])
                    targets = [str(target) for target in option.get("all_legal_targets", [])[:minimum]]
                else:
                    targets = targets_for(option, world)
                return CommandDescriptor(
                    HeadlessDeviceManager._DescriptorId(option), targets, payment_effect_ids(option))
            if on_prompt:
                command = on_prompt(prompt, world, targets_for)
                if command is not None:
                    return command
            return HeadlessDeviceManager._DefaultChoice(prompt)

        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            run_fixture(fixture, HeadlessDeviceManager(choice_provider=choose))

        self.assertEqual(error.call_count, 0, [str(call)[-2500:] for call in error.call_args_list])
        if "main" not in seen:
            return seen
        main_before, side_before = seen["before"]
        seen["removed"] = (main_before - seen["main"].threat, side_before - seen["side"].threat)
        return seen

    @staticmethod
    def one_main_two_side(option, main, side):
        return [main, side, side]

    def test_inconspicuous_must_remove_all_three(self):
        seen = self.play("spider_woman", "04038", self.one_main_two_side)

        self.assertEqual(seen["ranges"], [[3, 3]])
        self.assertEqual(seen["removed"], (1, 2))

    def test_torrential_rain_can_split_among_schemes(self):
        seen = self.play("storm", "36010", self.one_main_two_side)

        self.assertEqual(seen["ranges"], [[3, 3]])
        self.assertEqual(seen["removed"], (1, 2))

    def test_giant_help_in_giant_form_removes_all_four(self):
        def giant_form(prompt, world, targets_for):
            for option in prompt.options:
                if str(option.get("name", "")).startswith("AVENGER_GIANT"):
                    return CommandDescriptor(HeadlessDeviceManager._DescriptorId(option), [], [])
            return None

        seen = self.play("wasp", "13003", lambda option, main, side: [main, main, side, side],
                         on_prompt=giant_form)

        self.assertEqual(seen["ranges"], [[4, 4]])
        self.assertEqual(seen["removed"], (2, 2))

    def test_mutant_peacekeepers_targets_after_exhausting(self):
        # Phoenix exhausts herself and no allies; the targets are chosen
        # after the cost, sized by the THW actually exhausted.
        def on_prompt(prompt, world, targets_for):
            if prompt.event_name != "WhenPlayerChooseAbility":
                return None
            option = prompt.options[0]
            ids = [int(target) for target in option.get("all_legal_targets", [])]
            main = world.area_schemes_main.Get()[0].card.object_id
            if main not in ids:
                return None
            minimum = int(option.get("target_num_range")[0])
            side = world.FindCardsOnField(name="Breakin' & Takin'")[0].card.object_id
            picks = ([side] * 2 + [main] * minimum)[:minimum]
            targets_for(option, world)
            return CommandDescriptor(
                HeadlessDeviceManager._DescriptorId(option), [str(pick) for pick in picks], [])

        seen = self.play("phoenix", "34018", None, on_prompt=on_prompt)

        thwart = Engine.game.world.GetFirstPlayer().GetIdentity().thwart
        self.assertEqual(seen["ranges"], [[thwart, thwart]])
        self.assertEqual(sum(seen["removed"]), thwart)

    def test_shadowcat_can_pick_a_side_scheme_with_no_threat(self):
        # Consume the World (34030) is permanent, so it stays in play at 0.
        def on_prompt(prompt, world, targets_for):
            for option in prompt.options:
                bound = world.object_manager.card_dict.get(option.get("bind_id"))
                if bound and bound.face.paper.card_id == "46019":
                    scheme = world.FindCardsOnField(name="Consume the World")[0]
                    seen.update(scheme=scheme, threat=scheme.threat,
                                legal=[int(target) for target in option.get("all_legal_targets", [])])
                    return CommandDescriptor(
                        HeadlessDeviceManager._DescriptorId(option), [str(scheme.card.object_id)], [])
            return None

        seen = {}
        self.play("iceman", "46019", None,
                  extra=('Puzzle.PutIntoPlay("34030")', 'Puzzle.SetThreat("Consume the World", 0)'),
                  on_prompt=on_prompt)

        self.assertEqual(seen["threat"], 0)
        self.assertIn(seen["scheme"].card.object_id, seen["legal"])

if __name__ == "__main__":
    unittest.main()
