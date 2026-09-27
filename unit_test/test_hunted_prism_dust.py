"""Hunted (Tigra) with Prism Dust: a minion defeated on entry leaves no card stuck in processing."""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order
from engine.log import Log
from game.card.face.card_face import CardFace
from game.scene import SceneLoader
from game.scene.replay.operation import CommandDescriptor
from game.test.headless import HeadlessDeviceManager
from game.test.harness import initialize_database, run_scene_with_devices
from game.world.world_render import WorldRender


class TestHuntedPrismDust(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def play_hunted(self, *, minion_id="01110", use_prism=True, recover=False,
                    defeat_later=False, from_discard=False):
        scene = SceneLoader.NewScene("rhino", None, ["tigra"], 104)
        scene.rules = ["v18_all"]
        setup = iter((
            'puzzle.ClearHand()',
            'puzzle.ChangeFormFor(0, "Hero")',
            'puzzle.PutIntoPlay("50052")',
            'puzzle.CreateHandCards("56007")',
            f'puzzle.{"CreateEncounterDiscardPile" if from_discard else "CreateEncounterDeck"}("{minion_id}")',
            'puzzle.Exhaust("56001a")',
        ))
        after_play = iter(
            [f'puzzle.Damage("{minion_id}", 10)'] if defeat_later else
            ['puzzle.ChangeFormFor(0, "Identity")'] if recover else []
        )
        played = False
        recovered = False
        hunted = None
        summoned = None
        before_followup = None
        prism_windows = []
        ready_windows = []
        damage = []
        original_damage = CardFace.DealDamage

        def deal_damage(source, targets, value, effect, **kwargs):
            dealt = original_damage(source, targets, value, effect, **kwargs)
            if source.paper.card_id == "50052":
                damage.append((targets[0].paper.card_id, dealt))
            return dealt

        def choice(option, targets=None):
            if targets is None:
                targets = option["all_legal_targets"][:option["target_num_range"][0]]
            return CommandDescriptor(
                HeadlessDeviceManager._DescriptorId(option),
                [str(target) for target in targets], [],
            )

        def choose(prompt):
            nonlocal played, recovered, hunted, summoned, before_followup
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if len(devices.prompts) > 35:
                raise AssertionError("Unexpected repeated prompt")
            if prompt.event_name == "WhenPlayerInTurn":
                command = next(setup, None)
                if command:
                    Engine.game.controller_manager.console.SetCommand(command, world)
                    return CommandDescriptor()
                if not played:
                    option = next(option for option in prompt.options
                                  if option["name"] == "Play"
                                  and world.object_manager.card_dict[option["bind_id"]].face.paper.card_id == "56007")
                    hunted = world.object_manager.card_dict[option["bind_id"]].face
                    played = True
                    return choice(option)
                if before_followup is None:
                    before_followup = {
                        "hunted_discarded": hunted in player.discard_pile.Get(),
                        "hunted_processing": hunted.IsInProcessingArea(),
                        "attached": hunted.bind_face,
                        "exhausted": player.GetIdentity().IsExhaust(),
                        "minion_in_play": summoned.IsInPlay(),
                        "minion_stunned": summoned.IsStunned(),
                        "minion_confused": summoned.IsConfused(),
                    }
                command = next(after_play, None)
                if command:
                    Engine.game.controller_manager.console.SetCommand(command, world)
                    return CommandDescriptor()
                if recover and not recovered:
                    option = next(option for option in prompt.options if "Undercover_Work" in option["name"])
                    recovered = True
                    return choice(option)
                return None
            if prompt.event_name == "WhenPlayerChooseAbility":
                for option in prompt.options:
                    targets = [world.object_manager.card_dict[target].face for target in option["all_legal_targets"]]
                    target = next((face for face in targets if face.paper.card_id == minion_id
                                   and (face.card.area.flags.is_encounter_discard_pile if from_discard
                                        else face.card.area.flags.is_encounter_deck)), None)
                    if target and not summoned:
                        summoned = target
                        return choice(option, [target.card.object_id])
                    if recover and hunted in targets:
                        return choice(option, [hunted.card.object_id])
            for option in prompt.options:
                source = world.object_manager.card_dict[option["bind_id"]].face
                if source.paper.card_id == "50052" and prompt.event_name == "AfterCardEnterPlay":
                    prism_windows.append((hunted.IsInPlay(), hunted.bind_face))
                    if use_prism:
                        return choice(option)
                if source is hunted and prompt.event_name == "WhenUnitBeDefeated":
                    ready_windows.append(source.bind_face)
                    return choice(option)
            if prompt.show_cancel:
                return CommandDescriptor()
            return HeadlessDeviceManager._DefaultChoice(prompt)

        devices = HeadlessDeviceManager(choice_provider=choose)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch.object(CardFace, "DealDamage", new=deal_damage),
            patch.object(WorldRender, "ErrorOccurred") as errors,
            patch.object(Log, "Warn") as warnings,
        ):
            game = run_scene_with_devices(scene, devices)
        errors.assert_not_called()
        warnings.assert_not_called()
        self.assertIsNotNone(devices.stopped_prompt)
        self.assertEqual(devices.stopped_prompt.event_name, "WhenPlayerInTurn")
        return game.world.GetFirstPlayer(), hunted, summoned, before_followup, prism_windows, ready_windows, damage

    def test_lethal_entry_response_discards_unattached_hunted_and_does_not_ready_tigra(self):
        player, hunted, minion, state, prism, ready, damage = self.play_hunted()
        self.assertEqual(prism, [(False, None)])
        self.assertEqual(damage, [("01110", 2)])
        self.assertFalse(minion.IsInPlay())
        self.assertFalse(hunted.IsInProcessingArea())
        self.assertIn(hunted, player.discard_pile.Get())
        self.assertIsNotNone(player.discard_pile.FindCard(name="50052"))
        # Entry responses occur during the additional cost, before
        # Hunted enters play (RRG v1.8, Initiating Abilities, p. 25).
        self.assertEqual(ready, [])
        self.assertTrue(player.GetIdentity().IsExhaust())

    def test_undercover_work_can_retrieve_hunted_after_prism_dust_defeats_its_minion(self):
        player, hunted, minion, state, prism, ready, damage = self.play_hunted(recover=True)
        self.assertTrue(state["hunted_discarded"])
        self.assertIn(hunted, player.hand_cards.Get())
        self.assertIsNone(hunted.bind_face)

    def test_minion_selected_from_encounter_discard_also_leaves_hunted_recoverable(self):
        player, hunted, minion, state, prism, ready, damage = self.play_hunted(
            from_discard=True, recover=True,
        )
        self.assertEqual(prism, [(False, None)])
        self.assertEqual(damage, [("01110", 2)])
        self.assertFalse(minion.IsInPlay())
        self.assertTrue(state["hunted_discarded"])
        self.assertFalse(state["hunted_processing"])
        self.assertEqual(ready, [])
        self.assertIn(hunted, player.hand_cards.Get())

    def test_surviving_minion_is_attached_stunned_and_readies_tigra_when_defeated_later(self):
        player, hunted, minion, state, prism, ready, damage = self.play_hunted(
            minion_id="01172", defeat_later=True,
        )
        self.assertEqual(damage, [("01172", 2)])
        self.assertIs(state["attached"], minion)
        self.assertTrue(state["minion_in_play"])
        self.assertTrue(state["minion_stunned"])
        self.assertTrue(state["minion_confused"])
        self.assertTrue(state["exhausted"])
        self.assertEqual(ready, [minion])
        self.assertFalse(player.GetIdentity().IsExhaust())
        self.assertIn(hunted, player.discard_pile.Get())

    def test_declining_prism_dust_keeps_hunted_attached_and_preserves_its_interrupt(self):
        player, hunted, minion, state, prism, ready, damage = self.play_hunted(
            use_prism=False, defeat_later=True,
        )
        self.assertEqual(damage, [])
        self.assertIs(state["attached"], minion)
        self.assertTrue(state["minion_stunned"])
        self.assertFalse(state["minion_confused"])
        self.assertEqual(ready, [minion])
        self.assertFalse(player.GetIdentity().IsExhaust())
        self.assertIsNotNone(player.GetIdentity().GetInventoryDeck().FindCard(name="50052"))
        self.assertIn(hunted, player.discard_pile.Get())


if __name__ == "__main__":
    unittest.main()
