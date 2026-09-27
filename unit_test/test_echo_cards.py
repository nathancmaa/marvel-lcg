from __future__ import annotations

import importlib
from unittest import TestCase
from unittest.mock import Mock, patch

# Match the application's normal import order without starting the server.
from engine import Engine


class DaredevilAllyDiscountTests(TestCase):

    def test_played_event_cleanup_cannot_unregister_discount_twice(self):
        module = importlib.import_module("cards.pack.fne.echo.60039")
        response = module.GetAbilities()[0]

        cost_effect = Mock(is_unregister=False)
        cleanup_effect = Mock()
        daredevil = Mock()
        daredevil.effect.RegisterTemp.side_effect = [
            [cost_effect],
            [cleanup_effect],
        ]

        effect = Mock()
        effect.this.CastTo.return_value = daredevil
        effect.GetInitiator.return_value = Mock()

        response.operation(effect, Mock())

        discount_registration = daredevil.effect.RegisterTemp.call_args_list[0]
        self.assertFalse(discount_registration.kwargs["unregister_after_exec"])
        self.assertTrue(discount_registration.kwargs["until_round_end"])

        cleanup_ability = daredevil.effect.RegisterTemp.call_args_list[1].args[0]
        played_message = Mock()
        played_message.play_effect.ability.is_play = True

        with patch.object(module.Effects, "UnRegister") as unregister:
            cleanup_ability.operation(Mock(), played_message)
            unregister.assert_called_once_with([cost_effect])

            cost_effect.is_unregister = True
            cleanup_ability.operation(Mock(), played_message)
            unregister.assert_called_once_with([cost_effect])


class RaisedByTheKingpinTests(TestCase):

    def test_ongoing_effects_use_the_player_given_the_obligation(self):
        module = importlib.import_module("cards.pack.fne.echo.60060")
        abilities = module.GetAbilities()
        maya = Mock()
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = maya
        effect = Mock()
        effect.this.CastTo.return_value = obligation
        message = Mock()
        message.by_effect.GetInitiator.return_value = maya

        for ability in abilities[1:]:
            with self.subTest(event=ability.when.__name__):
                self.assertTrue(ability.conditions[-1](effect, message))

        obligation.GetGaveToPlayer.assert_called()
        effect.this.GetControlByPlayer.assert_not_called()

    def test_other_players_do_not_advance_or_bypass_the_obligation(self):
        module = importlib.import_module("cards.pack.fne.echo.60060")
        abilities = module.GetAbilities()
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = Mock(name="Maya")
        effect = Mock()
        effect.this.CastTo.return_value = obligation
        message = Mock()
        message.by_effect.GetInitiator.return_value = Mock(name="Other player")

        for ability in abilities[1:]:
            with self.subTest(event=ability.when.__name__):
                self.assertFalse(ability.conditions[-1](effect, message))


class PhotographicReflexesRealGameTests(TestCase):
    """Photographic Reflexes in real games, as Echo against Rhino.

    Echo plays Uppercut (cost 3) from hand and tucks it with Watch and
    Learn. Then the tucked Uppercut is played with Reflexes: its cost drops
    by 2, and a Reflexes copy the player kept out of the payment is
    discarded. A lone Reflexes used to be able to pay the remaining 1
    itself, so it played a 3-cost event for nothing.
    """

    @classmethod
    def setUpClass(cls):
        from game.test.harness import initialize_database
        initialize_database()

    def play_tucked_uppercut(self, extra_hand, pay_with):
        from game.test.headless import HeadlessDeviceManager
        from unit_test.fne_headless import build_scene, play

        state = {"phase": "first", "uppercut": None, "offer": None}

        def pay_face(world, key):
            uppercut = world.object_manager.card_dict[state["uppercut"]].face
            for effect in uppercut.effect.GetAll():
                if effect.ability.is_play:
                    for target in [None, *effect.context.all_legal_targets]:
                        found = effect.checker.cost_for_different_target.FindPayEffect(target, int(key))
                        if found:
                            return found.this
            raise AssertionError(f"no payer {key}")

        def payers_for(world, option, names):
            keys = [key for group in option["target_payment"].get("0", {}).get("payment", []) for key in group]
            chosen = []
            for name in names:
                for key in keys:
                    face = pay_face(world, key)
                    if (face.paper.card_id == name or face.name == name) and key not in chosen:
                        chosen.append(key)
                        break
            return chosen

        def choose(prompt):
            world = Engine.game.world
            player = world.GetFirstPlayer()
            if any(option.get("name") == "Watch_and_Learn" for option in prompt.options):
                return HeadlessDeviceManager._DefaultChoice(prompt)
            if prompt.event_name != "WhenPlayerInTurn":
                return None
            if state["phase"] == "first":
                uppercut = [face for face in player.hand_cards.Get() if face.paper.card_id == "01054"]
                for option in prompt.options:
                    if uppercut and option.get("name") == "Play" and option.get("bind_id") == uppercut[0].card.object_id:
                        state["uppercut"] = uppercut[0].card.object_id
                        state["phase"] = "tucked"
                        return self.command(option, payers_for(world, option, ["Energy", "Energy"]))
            if state["phase"] == "armed":
                state["phase"] = "done"
                offers = [
                    option for option in prompt.options
                    if option.get("name") == "Play" and option.get("bind_id") == state["uppercut"]
                ]
                if offers:
                    state["offer"] = [
                        pay_face(world, key).paper.card_id
                        for group in offers[0]["target_payment"]["0"]["payment"] for key in group
                    ]
                    if pay_with:
                        return self.command(offers[0], payers_for(world, offers[0], pay_with))
            return None

        def arm(_world):
            state["phase"] = "armed"
            return "Puzzle.End()"

        # Reflexes is in hand from the start: a card created straight into the
        # hand does not refresh whether the tucked event counts as in hand.
        hand = ", ".join(f'"{card_id}"' for card_id in ("01054", "01088", "01088", *extra_hand))
        run = play(
            build_scene("rhino", None, ["echo"], 5),
            [
                'Puzzle.ChangeFormFor(0, "Identity")',
                "Puzzle.ClearHand()",
                f"Puzzle.CreateHandCards({hand})",
                arm,
                "Puzzle.End()",
            ],
            on_prompt=choose,
            render=False,
        )
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(state["phase"], "done")
        player = run.world.GetFirstPlayer()
        rhino = [face for face in run.world.FindCardsOnField() if face.paper.card_id == "01094"][0]
        return {
            "offer": state["offer"],
            "hand": sorted(face.paper.card_id for face in player.hand_cards.Get()),
            "tucked": [face.paper.card_id for face in player.GetIdentity().GetPlacedCardArea().GetAll()],
            "rhino_damage": rhino.GetLostHealth(),
        }

    @staticmethod
    def command(option, payers):
        from game.scene.replay.operation import CommandDescriptor
        from game.test.headless import HeadlessDeviceManager
        return CommandDescriptor(
            HeadlessDeviceManager._DescriptorId(option),
            [str(option["all_legal_targets"][0])],
            payers,
        )

    def test_a_lone_reflexes_cannot_pay_for_the_event_it_plays(self):
        result = self.play_tucked_uppercut(["60040a"], [])
        self.assertEqual(result["offer"], [])
        self.assertEqual(result["tucked"], ["01054"])

    def test_reflexes_discards_itself_when_another_card_pays(self):
        result = self.play_tucked_uppercut(["60040a", "01088"], ["Energy"])
        self.assertEqual(result["hand"], [])
        self.assertEqual(result["tucked"], [])
        self.assertEqual(result["rhino_damage"], 10)

    def test_a_second_copy_can_pay_while_the_first_is_discarded(self):
        result = self.play_tucked_uppercut(["60040a", "60040b"], ["60040b"])
        self.assertEqual(sorted(result["offer"]), ["60040a", "60040b"])
        self.assertEqual(result["hand"], [])
        self.assertEqual(result["rhino_damage"], 10)

    def test_paying_with_every_copy_leaves_none_to_discard_and_the_play_fails(self):
        result = self.play_tucked_uppercut(["60040a", "60040b"], ["60040a", "60040b"])
        self.assertEqual(result["hand"], ["60040a", "60040b"])
        self.assertEqual(result["tucked"], ["01054"])
        self.assertEqual(result["rhino_damage"], 5)


class RaisedByTheKingpinRealGameTests(TestCase):
    """"You cannot deal damage to Kingpin": Maya's allies still can."""

    @classmethod
    def setUpClass(cls):
        from game.test.harness import initialize_database
        initialize_database()

    def kingpin_damage_after_attack(self, attacker_id):
        from game.scene.replay.operation import CommandDescriptor
        from game.test.headless import HeadlessDeviceManager
        from unit_test.fne_headless import build_scene, play

        state = {"armed": False, "attacked": False}

        def attack(prompt):
            if prompt.event_name != "WhenPlayerInTurn" or not state["armed"] or state["attacked"]:
                return None
            world = Engine.game.world
            attacker = [face for face in world.FindCardsOnField() if face.paper.card_id == attacker_id][0]
            kingpin = [face for face in world.FindCardsOnField() if face.paper.card_id == "60061"][0]
            for option in prompt.options:
                if option.get("name") == "Attack" and option.get("bind_id") == attacker.card.object_id:
                    state["attacked"] = True
                    return CommandDescriptor(
                        HeadlessDeviceManager._DescriptorId(option),
                        [str(kingpin.card.object_id)],
                        [],
                    )
            raise AssertionError(f"{attacker_id} cannot attack Kingpin: {prompt.options}")

        def arm(_world):
            state["armed"] = True
            return "Puzzle.End()"

        run = play(
            build_scene("rhino", None, ["echo"], 8),
            [
                'Puzzle.ChangeFormFor(0, "Identity")',
                'Puzzle.Reveal("60060")',
                'Puzzle.PutIntoPlay("60019")',
                arm,
                "Puzzle.End()",
            ],
            on_prompt=attack,
            render=False,
        )
        self.assertEqual(run.Exceptions(), [])
        self.assertTrue(state["attacked"])
        kingpin = [face for face in run.world.FindCardsOnField() if face.paper.card_id == "60061"][0]
        return kingpin.GetLostHealth()

    def test_echo_cannot_damage_kingpin(self):
        self.assertEqual(self.kingpin_damage_after_attack("60037a"), 0)

    def test_an_ally_can(self):
        self.assertGreater(self.kingpin_damage_after_attack("60019"), 0)
