from collections import Counter
from importlib import import_module
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.pack.tt.god_of_lies import (
    AddDefeatShatterCounters,
    ResolveStageTwoFocus,
    SwapAvatarWithRandomSetAside,
    _set_avatar_health_after_swap,
)


class TestGodOfLies(unittest.TestCase):

    project_root = Path(__file__).resolve().parents[1]
    scenario_path = project_root / "data" / "scenarios"
    scripts_path = project_root / "cards" / "pack" / "tt" / "god_of_lies"

    avatar_pairs = [
        "55029a,55029b",
        "55030a,55030b",
        "55031a,55031b",
        "55032a,55032b",
    ]
    synergy_environments = ["55052", "55053", "55054", "55055"]
    encounter_quantities = Counter({
        "55035": 1,
        "55036": 1,
        "55037": 2,
        "55038": 1,
        "55039": 1,
        "55040": 1,
        "55041": 1,
        "55042": 1,
        "55043": 1,
        "55044": 1,
        "55045": 1,
        "55046": 1,
        "55047": 2,
        "55048": 1,
        "55049": 2,
        "55050": 1,
        "55051": 3,
    })

    def load_scenario(self, expert: bool) -> dict:
        suffix = "_expert" if expert else ""
        return json.loads(
            (self.scenario_path / f"god_of_lies{suffix}.json").read_text(
                encoding="utf-8"
            )
        )

    def test_standard_scenario_has_the_complete_setup_and_encounter_deck(self):
        scenario = self.load_scenario(expert=False)

        self.assertEqual(scenario["villain"], ["55027a,55027b"])
        self.assertEqual(
            scenario["schemes"],
            ["55033a,55033b", "55028a,55028b"],
        )
        self.assertEqual(
            scenario["set_aside"],
            self.avatar_pairs
            + ["55034a,55034b"]
            + self.synergy_environments,
        )
        self.assertEqual(Counter(scenario["encounters"]), self.encounter_quantities)
        self.assertEqual(scenario["encounter_sets"], ["standard"])
        self.assertEqual(scenario["modular_sets"], ["trickster_magic"])
        self.assertFalse(scenario["expert"])

    def test_expert_scenario_only_adds_expert_rules(self):
        standard = self.load_scenario(expert=False)
        expert = self.load_scenario(expert=True)

        for field in (
            "version",
            "name",
            "villain",
            "schemes",
            "set_aside",
            "encounters",
            "modular_sets",
        ):
            self.assertEqual(expert[field], standard[field])
        self.assertTrue(expert["expert"])
        self.assertEqual(expert["encounter_sets"], ["standard", "expert"])

    def test_all_god_of_lies_cards_have_data_and_buildable_scripts(self):
        cards = json.loads(
            (self.project_root / "data" / "cards.json").read_text(
                encoding="utf-8"
            )
        )["tt"]
        by_id = {card["card_id"]: card for card in cards}
        expected_ids = {
            *(f"550{number:02d}{face}" for number in range(27, 35) for face in "ab"),
            *(f"550{number:02d}" for number in range(35, 56)),
        }

        self.assertTrue(expected_ids.issubset(by_id))
        for card_id in sorted(expected_ids):
            with self.subTest(card=card_id):
                self.assertTrue(by_id[card_id].get("name"))
                module = import_module(f"cards.pack.tt.god_of_lies.{card_id}")
                self.assertIsInstance(module.GetAbilities(), list)

    def test_side_scheme_icons_match_the_printed_cards(self):
        cards = json.loads(
            (self.project_root / "data" / "cards.json").read_text(
                encoding="utf-8"
            )
        )["tt"]
        by_id = {card["card_id"]: card for card in cards}

        self.assertEqual(
            by_id["55045"]["desc"],
            {
                "StartingThreat": "4",
                "Crisis": "1",
                "Boost": "1",
            },
        )
        self.assertEqual(
            by_id["55048"]["desc"],
            {
                "StartingThreat": "6",
                "Acceleration": "1",
                "Boost": "3",
            },
        )

    def test_draugr_buddy_has_printed_guard(self):
        cards = json.loads(
            (self.project_root / "data" / "cards.json").read_text(
                encoding="utf-8"
            )
        )["tt"]
        draugr_buddy = next(
            card for card in cards
            if card["card_id"] == "55037"
        )

        self.assertEqual(draugr_buddy["desc"]["Guard"], "1")

    def test_synergy_environment_bonuses_modify_event_values(self):
        effect = Mock()
        attack_message = Mock()
        thwart_message = Mock()

        attack_ability = import_module(
            "cards.pack.tt.god_of_lies.55052"
        ).GetAbilities()[0]
        thwart_ability = import_module(
            "cards.pack.tt.god_of_lies.55054"
        ).GetAbilities()[0]

        attack_ability.operation(effect, attack_message)
        thwart_ability.operation(effect, thwart_message)

        attack_message.DealAdditionalDamage.assert_called_once_with(4, effect)
        thwart_message.RemoveAdditionalThreat.assert_called_once_with(4, effect)

    def test_defeat_preserves_existing_shatter_counters_on_fading_figment(self):
        avatar = Mock()
        fading = Mock()
        avatar.GetCounters.return_value = 7
        avatar.card.back_faces = [fading]
        fading.HasTrait.return_value = True
        fading.CastTo.return_value = fading
        effect = Mock()

        with patch(
            "cards.pack.tt.god_of_lies.PlaceShatterCountersOnTheAvatarOfLokivillain",
            return_value=5,
        ) as place_counters:
            total = AddDefeatShatterCounters(avatar, effect)

        place_counters.assert_called_once()
        self.assertEqual(total, 7)
        fading.SetCounters.assert_called_once_with(7, "shatter", effect)

    def test_stories_and_lies_captures_current_hp_before_the_temporary_flip(self):
        active = Mock()
        active.health = 12
        active.HasTrait.return_value = False
        fading = Mock()
        fading.CastTo.return_value = fading
        active.card.face = fading
        next_avatar = Mock()
        effect = Mock()
        swapped_avatar = Mock()

        with patch(
            "cards.pack.tt.god_of_lies.Worlds.FindVillain",
            return_value=active,
        ), patch(
            "cards.pack.tt.god_of_lies.GetRandomSetAsideAvatar",
            return_value=next_avatar,
        ), patch(
            "cards.pack.tt.god_of_lies._swap_physical_avatar",
            return_value=swapped_avatar,
        ) as swap_avatar:
            result = SwapAvatarWithRandomSetAside(effect)

        active.card.Flip.assert_called_once_with(effect, call_reveal=False)
        swap_avatar.assert_called_once_with(
            fading,
            next_avatar,
            effect,
            preserved_health=12,
        )
        self.assertIs(result, swapped_avatar)

    def test_expert_stage_two_reveals_total_focus_after_flipping(self):
        avatar = Mock()
        intense_focus = Mock()
        intense_focus.IsName.side_effect = lambda name: name == "Intense Focus"
        avatar.GetAttachedAttachments.return_value = [intense_focus]
        effect = Mock()
        player = Mock()

        with patch(
            "cards.pack.tt.god_of_lies.FindAvatarOfLoki",
            return_value=avatar,
        ), patch(
            "cards.pack.tt.god_of_lies.Worlds.IsExpert",
            return_value=True,
        ):
            resolved = ResolveStageTwoFocus(effect, player)

        self.assertTrue(resolved)
        intense_focus.card.Flip.assert_called_once_with(
            effect,
            call_reveal=True,
        )

    def test_lethal_damage_advances_loki_stage_two_at_full_health(self):
        module = import_module("cards.pack.tt.god_of_lies.55027a")
        lethal_transition = module.GetAbilities()[1]
        effect = Mock()
        loki = Mock()
        first_player = Mock()
        rule_effect = Mock()
        message = Mock()
        effect.this.CastTo.return_value = loki
        effect.world.GetFirstPlayer.return_value = first_player

        with patch.object(
            module,
            "GameRule",
            return_value=rule_effect,
        ) as game_rule:
            lethal_transition.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        loki.ResetHealth.assert_called_once_with(effect)
        loki.SetHealth.assert_not_called()
        game_rule.assert_called_once_with(loki, initiator=first_player)
        loki.card.Flip.assert_called_once_with(rule_effect)

    def test_swap_reapplies_focus_once_then_restores_current_hp(self):
        avatar = Mock()
        intense_focus = Mock()
        intense_focus.IsName.side_effect = lambda name: name == "Intense Focus"
        avatar.GetAttachedAttachments.return_value = [intense_focus]
        effect = Mock()

        with patch(
            "cards.pack.tt.god_of_lies.Worlds.ConvertPerPlayerIconToInt",
            return_value=2,
        ) as convert_bonus:
            _set_avatar_health_after_swap(avatar, effect, preserved_health=12)

        avatar.ResetHealth.assert_called_once_with(effect)
        convert_bonus.assert_called_once_with("2*", effect)
        avatar.GainHealthAndMaxHealth.assert_called_once_with(2, effect)
        avatar.SetHealth.assert_called_once_with(12, effect)

if __name__ == "__main__":
    unittest.main()
