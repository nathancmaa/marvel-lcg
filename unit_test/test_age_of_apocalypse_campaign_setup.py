"""Age of Apocalypse campaign setup (ported from the sdolle1775 fork).

Cards made during setup are staged in the set-aside deck here, not nowhere.
"""

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.pack.aoa.campaign_setup import (
    AddPreviousMissionRewardsAndPenalties,
    CampaignSetup,
    SetupMission,
    ShuffleAgeOfApocalypseSetIntoEncounterDeck,
    _log_choice,
)


class TestAgeOfApocalypseCampaignSetup(unittest.TestCase):

    project_root = Path(__file__).resolve().parents[1]
    missions = ["45166a", "45167a", "45168a", "45169a"]
    overseers = ["45179a", "45180a", "45181a", "45182a", "45183a"]

    def test_menu_tracks_outcomes_without_per_scenario_overrides(self):
        html = (self.project_root / "public" / "scene.html").read_text(
            encoding="utf-8"
        )

        for level in range(1, 5):
            self.assertNotIn(
                f'description: "Scenario {level} Mission Side Scheme"',
                html,
            )
        for level in range(1, 6):
            self.assertNotIn(
                f'description: "Scenario {level} Overseer"',
                html,
            )

        self.assertIn(
            '{ description: "Mission Side Schemes Removed from campaign", '
            'type: "checkbox"',
            html,
        )
        self.assertIn(
            '{ description: "Mission Side Schemes Defeated", '
            'type: "checkbox"',
            html,
        )
        self.assertIn(
            '{ description: "Overseers Defeated", type: "checkbox"',
            html,
        )

        for player_number in range(1, 5):
            self.assertIn(
                f'{{ description: "Player {player_number} Campaign Ally", '
                'type: "checkbox"',
                html,
            )
            self.assertNotIn(
                f'{{ description: "Player {player_number} Campaign Ally", '
                'type: "select"',
                html,
            )

    def test_setup_randomizes_only_from_unchecked_campaign_pools(self):
        ability = SetupMission(2)
        mission_team = MagicMock()
        effect = SimpleNamespace(world=MagicMock())
        selections = []
        requested_log_keys = []

        def log_list(key, check_effect):
            requested_log_keys.append(key)
            if key == "Mission Side Schemes Removed from campaign":
                return ["45166a", "45168a"]
            if key == "Overseers Defeated":
                return ["45180a"]
            return []

        def random_available(all_ids, unavailable, check_effect):
            selections.append((list(all_ids), set(unavailable)))
            return ""

        with patch(
            "cards.pack.aoa.campaign_setup._log_list",
            side_effect=log_list,
        ), patch(
            "cards.pack.aoa.campaign_setup._random_available",
            side_effect=random_available,
        ), patch(
            "cards.pack.aoa.campaign_setup.Worlds.FindCardsOnField",
            return_value=[],
        ), patch(
            "cards.pack.aoa.campaign_setup.Worlds.GetFirstPlayer",
            return_value=MagicMock(),
        ), patch(
            "game.operate.campaign_logs.CampaignLog.SetStr",
        ), patch(
            "cards.pack.aoa.campaign_setup.CardFactory.GenerateCard",
            return_value=SimpleNamespace(face=mission_team),
        ):
            ability.operation(effect, SimpleNamespace())

        self.assertEqual(
            requested_log_keys,
            [
                "Mission Side Schemes Removed from campaign",
                "Overseers Defeated",
            ],
        )
        self.assertEqual(selections[0], (self.missions, {"45166a", "45168a"}))
        self.assertEqual(selections[1], (self.overseers, {"45180a"}))

    def test_defeated_rewards_require_both_outcome_checkboxes(self):
        ability = AddPreviousMissionRewardsAndPenalties(2)
        player = SimpleNamespace(
            player_id=0,
            MayChooseOneAbility=MagicMock(),
        )
        effect = SimpleNamespace(world=MagicMock())

        def log_list(key, check_effect):
            if key in (
                "Mission Side Schemes Removed from campaign",
                "Mission Side Schemes Defeated",
            ):
                return self.missions
            return []

        def log_value(key, check_effect):
            values = {
                "Player 1 Campaign Aspect Upgrade": "upgrade-card",
                "Player 1 Campaign Aspect Support": "support-card",
            }
            return values.get(key, "")

        with patch(
            "cards.pack.aoa.campaign_setup._log_list",
            side_effect=log_list,
        ), patch(
            "cards.pack.aoa.campaign_setup.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            side_effect=log_value,
        ), patch(
            "cards.pack.aoa.campaign_setup._log_choice",
            return_value="45172",
        ), patch(
            "cards.pack.aoa.campaign_setup._generate_into_player_deck",
        ) as generate:
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_called_once()
        self.assertEqual(
            generate.call_args_list,
            [
                call("upgrade-card", player, effect),
                call("support-card", player, effect),
                call("45172", player, effect),
            ],
        )

    def test_removed_only_applies_not_defeated_campaign_effects(self):
        ability = AddPreviousMissionRewardsAndPenalties(2)
        player = SimpleNamespace(
            player_id=0,
            MayChooseOneAbility=MagicMock(),
        )
        sea_wall = MagicMock()
        effect = SimpleNamespace(world=MagicMock())

        def log_list(key, check_effect):
            if key == "Mission Side Schemes Removed from campaign":
                return self.missions
            return []

        with patch(
            "cards.pack.aoa.campaign_setup._log_list",
            side_effect=log_list,
        ), patch(
            "cards.pack.aoa.campaign_setup.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "cards.pack.aoa.campaign_setup._generate_into_player_deck",
        ) as generate, patch(
            "cards.pack.aoa.campaign_setup.CardFactory.GenerateCard",
            return_value=SimpleNamespace(face=sea_wall),
        ) as generate_card, patch(
            "cards.pack.aoa.campaign_setup.Worlds.AsideDeck",
            return_value="aside",
        ), patch(
            "cards.pack.aoa.campaign_setup.Faces.ShuffleAllTo",
        ) as shuffle:
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_not_called()
        generate.assert_called_once_with("45178", player, effect)
        generate_card.assert_called_once_with("45177", "aside", effect.world)
        shuffle.assert_called_once_with([sea_wall], "EncounterDeck", effect)

    def test_defeated_checkbox_alone_does_not_apply_an_outcome(self):
        ability = AddPreviousMissionRewardsAndPenalties(2)
        player = SimpleNamespace(
            player_id=0,
            MayChooseOneAbility=MagicMock(),
        )
        effect = SimpleNamespace(world=MagicMock())

        def log_list(key, check_effect):
            if key == "Mission Side Schemes Defeated":
                return self.missions
            return []

        with patch(
            "cards.pack.aoa.campaign_setup._log_list",
            side_effect=log_list,
        ), patch(
            "cards.pack.aoa.campaign_setup.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "cards.pack.aoa.campaign_setup._generate_into_player_deck",
        ) as generate, patch(
            "cards.pack.aoa.campaign_setup.CardFactory.GenerateCard",
        ) as generate_card:
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_not_called()
        generate.assert_not_called()
        generate_card.assert_not_called()

    def test_campaign_ally_checkbox_value_is_read_as_a_list(self):
        effect = SimpleNamespace()

        with patch(
            "game.operate.campaign_logs.CampaignLog.GetListInternal",
            return_value=["45174"],
        ) as read:
            self.assertEqual(
                _log_choice(
                    "Player 1 Campaign Ally",
                    ["45172", "45173", "45174", "45175"],
                    effect,
                ),
                "45174",
            )

        read.assert_called_once_with("Player 1 Campaign Ally", effect)

    def test_every_campaign_scenario_includes_the_modular_setup_once(self):
        scenario_scripts = {
            "cards/pack/aoa/unus/45062a.py": 1,
            "cards/pack/aoa/four_horsemen/45085a.py": 2,
            "cards/pack/aoa/apocalypse/45103a.py": 3,
            "cards/pack/aoa/dark_beast/45121a.py": 4,
            "cards/pack/aoa/en_sabah_nur/45147a.py": 5,
        }
        for relative_path, level in scenario_scripts.items():
            with self.subTest(scenario=level):
                source = (self.project_root / relative_path).read_text(
                    encoding="utf-8"
                )
                self.assertEqual(source.count(f"*CampaignSetup({level})"), 1)

                abilities = CampaignSetup(level)
                modular_abilities = [
                    ability
                    for ability in abilities
                    if (
                        "ShuffleAgeOfApocalypseSetIntoEncounterDeck"
                        in ability.operation.__qualname__
                    )
                ]
                self.assertEqual(len(modular_abilities), 1)

    def test_modular_setup_shuffles_the_complete_set(self):
        ability = ShuffleAgeOfApocalypseSetIntoEncounterDeck()
        effect = SimpleNamespace(world=MagicMock())
        faces = [MagicMock() for _ in range(4)]

        with patch(
            "cards.pack.aoa.campaign_setup.CardFactory.GenerateCard",
            side_effect=[SimpleNamespace(face=face) for face in faces],
        ) as generate, patch(
            "cards.pack.aoa.campaign_setup.Worlds.AsideDeck",
            return_value="aside",
        ), patch(
            "cards.pack.aoa.campaign_setup.Faces.ShuffleAllTo",
        ) as shuffle:
            ability.operation(effect, SimpleNamespace())

        self.assertEqual(
            generate.call_args_list,
            [
                call("45164", "aside", effect.world),
                call("45164", "aside", effect.world),
                call("45165", "aside", effect.world),
                call("45165", "aside", effect.world),
            ],
        )
        shuffle.assert_called_once_with(faces, "EncounterDeck", effect)


if __name__ == "__main__":
    unittest.main()
