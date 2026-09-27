from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

# Match the application's import order without initializing the server.
from engine import Engine
from build import Build
from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.selector.selector_target_helper import get_TeamUp


ROOT = Path(__file__).resolve().parents[1]
daredevil_pack = importlib.import_module("cards.pack.fne.daredevil")


class DaredevilScriptLoadTests(TestCase):

    def test_every_daredevil_script_builds_its_abilities(self):
        modules = [
            "cards.pack.fne.daredevil.60001a",
            "cards.pack.fne.daredevil.60001b",
            *(f"cards.pack.fne.daredevil.{card_id}" for card_id in range(60002, 60019)),
            "cards.pack.fne.daredevil.60032",
            *(f"cards.pack.fne.{card_id}" for card_id in range(60019, 60032)),
            *(f"cards.pack.fne.daredevil_nemesis.{card_id}" for card_id in range(60033, 60037)),
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                abilities = importlib.import_module(module_name).GetAbilities()
                self.assertTrue(abilities)

    def test_every_daredevil_card_face_can_be_created(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        world = Mock()
        world.GetPlayerNumIcon.return_value = 1
        card_ids = [
            "60001a",
            "60001b",
            *(f"{card_id}" for card_id in range(60002, 60037)),
        ]

        with patch.object(Build, "release", False):
            for card_id in card_ids:
                with self.subTest(card_id=card_id):
                    paper = CardsDB.FindCardPaper(card_id)
                    face = CardFactory.CreateFace(paper, world)
                    self.assertEqual(face.paper.card_id, card_id)

    def test_starter_deck_has_legal_preconstructed_counts(self):
        with (ROOT / "deck/starter/daredevil.json").open(encoding="utf-8") as source:
            deck = json.load(source)

        self.assertEqual(len(deck["hero_deck"]), 15)
        self.assertEqual(len(deck["player_deck"]), 25)
        self.assertEqual(len(deck["set_aside"]), 5)
        self.assertEqual(len(deck["obligations"]), 1)
        self.assertEqual(len(deck["nemesis_set"]), 5)

    def test_chance_encounter_reprint_reuses_the_existing_card_image(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        self.assertEqual(CardsDB.FindCardPaper("60025").pic_id, "26034")

    def test_daredevil_has_two_printed_thwart(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        self.assertEqual(CardsDB.FindCardPaper("60001a").desc["THW"], "2")


class SenseDeckTests(TestCase):

    def test_both_identity_forms_keep_the_top_sense_card_faceup(self):
        for card_id in ("60001a", "60001b"):
            with self.subTest(card_id=card_id):
                module = importlib.import_module(f"cards.pack.fne.daredevil.{card_id}")
                abilities = module.GetAbilities()
                faceup_abilities = [
                    ability for ability in abilities
                    if ability.when.__name__ in {
                        "AfterCardsMoved",
                        "AfterDeckShuffle",
                        "AfterUnitChangeForm",
                        "WhenUnitWouldChangeForm",
                    }
                ]
                self.assertEqual(len(faceup_abilities), 4)

    def test_revealing_sense_deck_shows_every_card_and_clears_cached_access(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60001b")
        faceup_ability = next(
            ability for ability in module.GetAbilities()
            if ability.when.__name__ == "AfterDeckShuffle"
        )
        top_sense = Mock()
        other_sense = Mock()
        for sense in (top_sense, other_sense):
            sense.card.can_state.is_like_in_hand = False
        sense_deck = Mock()
        sense_deck.GetTop.return_value = top_sense
        sense_deck.GetAll.return_value = [other_sense, top_sense]
        player = Mock()
        player.special_decks = {daredevil_pack.SENSE_DECK: sense_deck}
        effect = Mock()
        effect.GetInitiator.return_value = player

        faceup_ability.operation(effect, Mock())

        for sense in (top_sense, other_sense):
            self.assertIsNone(sense.card.can_state.is_like_in_hand)
            self.assertTrue(sense.FlipTo.called)
        top_sense.FlipTo.assert_any_call(effect, face_up=True, ui_look_at=True)
        other_sense.FlipTo.assert_called_once_with(
            effect,
            face_up=True,
            ui_look_at=False,
        )

    def test_daredevil_can_treat_only_the_top_sense_as_in_hand(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60001a")
        like_in_hand = module.GetAbilities()[0]
        top_sense = Mock()
        other_sense = Mock()
        sense_deck = Mock()
        sense_deck.GetTop.return_value = top_sense
        player = Mock()
        player.special_decks = {daredevil_pack.SENSE_DECK: sense_deck}
        effect = Mock()
        effect.GetInitiator.return_value = player

        self.assertTrue(
            like_in_hand.conditions[-1](effect, Mock(which_face=top_sense))
        )
        self.assertFalse(
            like_in_hand.conditions[-1](effect, Mock(which_face=other_sense))
        )

    def test_sense_upgrade_leaving_play_goes_to_bottom_in_both_forms(self):
        for card_id in ("60001a", "60001b"):
            with self.subTest(card_id=card_id):
                module = importlib.import_module(
                    f"cards.pack.fne.daredevil.{card_id}"
                )
                ability = next(
                    ability for ability in module.GetAbilities()
                    if ability.when.__name__ == "WhenCardWouldLeavePlay"
                )
                sense_deck = Mock()
                player = Mock()
                player.special_decks = {
                    daredevil_pack.SENSE_DECK: sense_deck,
                }
                effect = Mock()
                effect.GetInitiator.return_value = player
                sense = Mock()
                message = Mock(trigger=sense, into_area=Mock())

                with patch.object(
                    daredevil_pack.Faces,
                    "MoveAllToDeck",
                ) as move_to_deck:
                    ability.operation(effect, message)

                message.SetBeInstead.assert_called_once_with(effect)
                move_to_deck.assert_called_once_with(
                    [sense],
                    sense_deck,
                    "Bottom",
                    effect,
                )

    def test_choose_sense_plays_selected_card_without_resource_cost(self):
        sense = Mock()
        sense_deck = Mock()
        sense_deck.GetAll.return_value = [sense]
        player = Mock()
        player.special_decks = {daredevil_pack.SENSE_DECK: sense_deck}
        player.MayChooseFace.return_value = sense
        player.PlayCardsLikeInTurn.return_value = [sense]
        effect = Mock()

        played = daredevil_pack.ChooseAndPlaySense(player, effect)

        self.assertIs(played, sense)
        player.PlayCardsLikeInTurn.assert_called_once_with(
            [sense],
            effect,
            ignore_resources_cost=True,
            forced=True,
            if_not_play_discard_it=False,
        )


class DaredevilAbilityTests(TestCase):

    def test_contingency_planning_accepts_chance_encounter_without_a_target_in_play(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        world = Mock()
        world.GetPlayerNumIcon.return_value = 1
        chance_encounter = CardFactory.CreateFace(
            CardsDB.FindCardPaper("60025"),
            world,
        )
        identity_upgrade = CardFactory.CreateFace(
            CardsDB.FindCardPaper("60017"),
            world,
        )
        module = importlib.import_module("cards.pack.fne.60030")
        action = next(
            ability for ability in module.GetAbilities()
            if ability.flags.is_action
        )
        finder = action.selectors[0].selector_filter.finder
        effect = Mock()

        self.assertTrue(finder.Check(chance_encounter, effect))
        self.assertFalse(finder.Check(identity_upgrade, effect))

    def test_superior_taste_treats_you_as_your_identity(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60006")
        factory_module = importlib.import_module("game.ability.factory.scheme")
        response = next(
            ability for ability in module.GetAbilities()
            if ability.when.__name__ == "AfterSchemeRemoveThreat"
        )
        effect = Mock()
        source = Mock()
        message = Mock()
        message.would_remove_message.by_face = source

        with patch.object(
            factory_module.Condition,
            "CheckWhichCard",
            return_value=True,
        ) as check_card:
            self.assertTrue(response.conditions[1](effect, message))

        check_card.assert_called_once_with("YourIdentity", source, effect)

    def test_know_your_enemy_rechecks_crisis_before_each_threat_removal(self):
        module = importlib.import_module("cards.pack.fne.60023")
        ability = module.GetAbilities()[1]
        event = Mock()
        event.CastTo.return_value = event
        crisis_scheme = Mock()
        main_scheme = Mock()
        main_scheme.CanBeThwartBy.side_effect = [False, True]
        crisis_scheme.CanBeThwartBy.return_value = True
        player = Mock()
        player.AskChooseFace.side_effect = [crisis_scheme, main_scheme]
        effect = Mock(this=event)
        effect.GetInitiator.return_value = player

        with patch.object(
            module.Worlds,
            "GetOnFieldSchemes",
            side_effect=[
                [main_scheme, crisis_scheme],
                [main_scheme],
            ],
        ):
            ability.operation(effect, Mock())

        self.assertEqual(
            player.AskChooseFace.call_args_list[0].args[0],
            [crisis_scheme],
        )
        self.assertEqual(
            player.AskChooseFace.call_args_list[1].args[0],
            [main_scheme],
        )
        self.assertEqual(
            [call.args for call in event.RemoveThreatFromSchemes.call_args_list],
            [
                ([crisis_scheme], 1, effect),
                ([main_scheme], 1, effect),
            ],
        )

    def test_dance_with_the_devil_teamup_selector_accepts_an_upgrade(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        world = Mock()
        world.GetPlayerNumIcon.return_value = 1
        paper = CardsDB.FindCardPaper("60031")
        dance_with_the_devil = CardFactory.CreateFace(paper, world)
        team_up_units = [Mock(), Mock()]

        with patch.object(
            dance_with_the_devil,
            "GetTeamUpUnits",
            return_value=team_up_units,
        ):
            self.assertEqual(
                get_TeamUp(Mock(this=dance_with_the_devil)),
                team_up_units,
            )

    def test_focus_the_senses_allows_both_identity_forms_to_remove_threat(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60012")
        cannot_remove = module.GetAbilities()[1]
        effect = Mock()
        message = Mock()

        message.by_face.IsName.side_effect = lambda name: name == "Daredevil"
        self.assertFalse(cannot_remove.conditions[-1](effect, message))

        message.by_face.IsName.side_effect = lambda name: name == "Matt Murdock"
        self.assertFalse(cannot_remove.conditions[-1](effect, message))

        message.by_face.IsName.return_value = False
        message.by_face.IsName.side_effect = None
        self.assertTrue(cannot_remove.conditions[-1](effect, message))

    def test_stealth_training_requires_exact_side_scheme_defeat(self):
        module = importlib.import_module("cards.pack.fne.60028")
        ability = module.GetAbilities()[1]
        condition = ability.conditions[-1]
        side_scheme = Mock(spec=module.SchemeSide2)
        side_scheme.threat = 0
        property = Mock(is_divided=False)
        property.GetThwart.return_value = 3
        after = Mock(
            scheme=side_scheme,
            remove_threat=3,
            would_thw_message=Mock(property=property),
        )
        message = Mock(trigger=Mock(), after_thw_messages=[after])

        self.assertTrue(condition(Mock(), message))

        after.remove_threat = 2
        self.assertFalse(condition(Mock(), message))

    def test_cross_examination_adds_optional_damage_per_attached_upgrade(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60008")
        ability = module.GetAbilities()[0]
        event = Mock()
        event.CastTo.return_value = event
        target = Mock()
        target.GetInventoryDeck.return_value.FindCards.return_value = [Mock(), Mock()]
        player = Mock()
        player.AskChooseOneText.return_value = 2
        effect = Mock(this=event, targets=[target])
        effect.GetInitiator.return_value = player

        ability.operation(effect, Mock())

        event.DealDamage.assert_called_once_with([target], 5, effect)

    def test_elektra_redirects_consequential_damage_to_daredevil(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60007")
        ability = module.GetAbilities()[0]
        daredevil = Mock()
        player = Mock()
        player.GetHero.return_value = daredevil
        effect = Mock()
        effect.GetInitiator.return_value = player
        message = Mock()

        ability.operation(effect, message)

        message.ChangeDealtToTarget.assert_called_once_with(daredevil, effect)


class SenseInterruptRealGameTests(TestCase):
    """Acute Tactility and Enhanced Olfaction in real games.

    "When you defeat attached enemy or remove the last threat from attached
    scheme" is offered when Daredevil takes the last threat off any scheme
    (a main scheme is not defeated by that) or defeats the enemy, and not
    when an ally does it. The discarded Sense goes back to the Sense deck in
    time for Focus the Senses to put it back into play.
    """

    SENSES = ("60002", "60003")

    @classmethod
    def setUpClass(cls):
        from game.test.harness import initialize_database
        initialize_database()

    def run_table(self, sense_id, setup, acts, attach_to, seed=99):
        """Play Rhino as Daredevil: set up, attach the Sense, then act.

        ``acts`` are (option name, acting card id, target card id) actions
        taken on the player's turn, with Daredevil readied between them.
        Returns the run and what the Sense's interrupt prompt saw (None if it
        was never offered) and Focus the Senses' put-into-play prompt.
        """
        from game.scene.replay.operation import CommandDescriptor
        from game.test.headless import HeadlessDeviceManager
        from unit_test.fne_headless import build_scene, play

        state = {"armed": False, "acted": 0, "interrupt": None, "put": None}

        def face_of(world, card_id):
            found = [face for face in world.FindCardsOnField() if face.paper.card_id == card_id]
            return found[0] if found else None

        def choose(prompt):
            world = Engine.game.world
            player = world.GetFirstPlayer()
            for option in prompt.options:
                bind = world.object_manager.card_dict.get(option.get("bind_id"))
                if prompt.ability_type == "Interrupt" and bind and bind.face.paper.card_id == sense_id:
                    scheme_or_enemy = face_of(world, attach_to)
                    state["interrupt"] = {
                        "event": prompt.event_name,
                        "threat": getattr(scheme_or_enemy, "threat", None),
                        "exhausted": player.GetIdentity().IsExhaust(),
                    }
                    return CommandDescriptor(
                        HeadlessDeviceManager._DescriptorId(option),
                        [str(target) for target in option.get("all_legal_targets", [])],
                        [],
                    )
                if option.get("name") == "Choose_Sense_upgrades_to_put_into_play":
                    state["put"] = {
                        "targets": list(option.get("all_legal_targets", [])),
                        "exhausted": player.GetIdentity().IsExhaust(),
                    }
                    return None
            if prompt.event_name == "WhenPlayerChooseAbility" and not state["armed"]:
                target = face_of(world, attach_to)
                for option in prompt.options:
                    if target and target.card.object_id in option.get("all_legal_targets", []):
                        return CommandDescriptor(
                            HeadlessDeviceManager._DescriptorId(option),
                            [str(target.card.object_id)],
                            [],
                        )
            if prompt.event_name == "WhenPlayerInTurn" and state["armed"] and state["acted"] < len(acts):
                name, actor_id, target_id = acts[state["acted"]]
                actor = face_of(world, actor_id)
                target = face_of(world, target_id)
                if actor.IsExhaust():
                    return None  # the next command readies Daredevil
                for option in prompt.options:
                    if option.get("name") == name and option.get("bind_id") == actor.card.object_id:
                        state["acted"] += 1
                        return CommandDescriptor(
                            HeadlessDeviceManager._DescriptorId(option),
                            [str(target.card.object_id)],
                            [],
                        )
                raise AssertionError(f"no {name} for {actor_id} in {prompt.options}")
            return None

        def arm(_world):
            state["armed"] = True
            return "Puzzle.End()"

        commands = [
            'Puzzle.ChangeFormFor(0, "Identity")',
            *setup,
            f'Puzzle.PutIntoPlay("{sense_id}")',
            arm,
            "Puzzle.Ready(c1)",
            "Puzzle.End()",
        ]
        run = play(
            build_scene("rhino", None, ["daredevil"], seed),
            commands,
            on_prompt=choose,
            render=False,
            max_prompts=80,
        )
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(state["acted"], len(acts))
        return run, state

    def test_removing_the_last_threat_from_focus_the_senses_lets_it_replay_the_sense(self):
        for sense_id in self.SENSES:
            with self.subTest(sense=sense_id):
                # Focus starts with 4 threat; Daredevil (THW 2) thwarts once,
                # readies, then takes the last 2 off.
                run, state = self.run_table(
                    sense_id,
                    ['Puzzle.PutIntoPlay("60012")'],
                    [("Thwart", "60001a", "60012")] * 2,
                    "60012",
                )
                self.assertEqual(
                    state["interrupt"],
                    {"event": "WhenSchemeWouldRemoveThreat", "threat": 2, "exhausted": True},
                )
                self.assertIsNotNone(state["put"])
                from cards.pack.fne.daredevil import GetSenseDeck
                deck = GetSenseDeck(run.world.GetFirstPlayer())
                returned = [face for face in deck.GetAll() if face.paper.card_id == sense_id]
                self.assertTrue(any(face.card.object_id in state["put"]["targets"] for face in returned))
                if sense_id == "60002":
                    self.assertFalse(state["put"]["exhausted"])

    def test_removing_the_last_main_scheme_threat_is_offered(self):
        for sense_id in self.SENSES:
            with self.subTest(sense=sense_id):
                run, state = self.run_table(
                    sense_id,
                    ['Puzzle.SetThreat("01097b", 2)'],
                    [("Thwart", "60001a", "01097b")],
                    "01097b",
                )
                self.assertEqual(state["interrupt"]["event"], "WhenSchemeWouldRemoveThreat")
                self.assertEqual(state["interrupt"]["threat"], 2)

    def test_defeating_the_attached_minion_is_offered(self):
        for sense_id in self.SENSES:
            with self.subTest(sense=sense_id):
                run, state = self.run_table(
                    sense_id,
                    ['Puzzle.PutIntoPlay("01101")', 'Puzzle.Damage("01101", 1)'],
                    [("Attack", "60001a", "01101")],
                    "01101",
                )
                self.assertIsNotNone(state["interrupt"])
                self.assertEqual(state["interrupt"]["event"], "WhenUnitWouldBeDefeated")

    def test_an_ally_thwarting_the_attached_side_scheme_is_not_you(self):
        for sense_id in self.SENSES:
            with self.subTest(sense=sense_id):
                run, state = self.run_table(
                    sense_id,
                    ['Puzzle.PutIntoPlay("01107")', 'Puzzle.PutIntoPlay("60019")'],
                    [("Thwart", "60019", "01107")],
                    "01107",
                )
                self.assertIsNone(state["interrupt"])
                side = [face for face in run.world.FindCardsOnField() if face.paper.card_id == "01107"]
                self.assertEqual(side, [], "Blindspot should have cleared the side scheme")
