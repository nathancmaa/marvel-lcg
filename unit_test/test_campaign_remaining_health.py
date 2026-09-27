from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.pack.aoa.campaign_setup import (
    ExpertCampaignEachPlayerMayHealAtMissionThreatCost,
    ExpertCampaignSetPlayersHPToTheirRemainingHP,
)
from game.ability.factory.campaign import AbilityFactoryCampaign
from game.message import Message


class TestCampaignRemainingHealth(unittest.TestCase):

    def _run_generic(self, logged):
        ability = AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id="agents_of_shield",
        )
        identity = MagicMock()
        identity.max_health = 10
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
        )
        effect = SimpleNamespace()

        def log(key, by_effect):
            return logged.get(key, "")

        with patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            side_effect=log,
        ):
            ability.operation(effect, SimpleNamespace())
        return ability, identity, effect

    def test_remaining_health_is_applied_during_campaign_setup(self):
        ability, identity, effect = self._run_generic(
            {"Player 1 Remaining hit points": "4"})

        self.assertIs(ability.when, Message.WhenCampaignSetup)
        identity.SetHealth.assert_called_once_with(4, effect)

    def test_remaining_health_is_expert_only(self):
        # The campaign guides carry damage only in an expert campaign.
        ability = AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id="agents_of_shield",
        )
        effect = SimpleNamespace()
        message = SimpleNamespace()

        with patch(
            "game.operate.worlds.Worlds.IsCampaign",
            return_value=True,
        ), patch(
            "game.operate.worlds.Worlds.IsCampaignSelected",
            return_value=True,
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=False,
        ):
            self.assertFalse(all(
                condition(effect, message) for condition in ability.conditions
            ))

    def test_a_logged_zero_is_a_defeated_hero_not_an_unset_value(self):
        _, identity, effect = self._run_generic(
            {"Player 1 Remaining hit points": "0"})

        identity.SetHealth.assert_called_once_with(1, effect)

    def test_nothing_logged_leaves_the_identity_alone(self):
        _, identity, _ = self._run_generic({})

        identity.SetHealth.assert_not_called()

    def test_logged_hit_points_are_capped_at_the_current_maximum(self):
        _, identity, effect = self._run_generic(
            {"Remaining hit points P1": "14"})

        identity.SetHealth.assert_called_once_with(10, effect)

    def test_aoa_standard_campaign_with_remaining_health_skips_heal(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=MagicMock()),
            MayChooseOneAbility=MagicMock(),
        )
        effect = SimpleNamespace()

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=MagicMock(),
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=False,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="4",
        ):
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_not_called()

    def test_aoa_expert_campaign_without_remaining_health_skips_heal(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(),
            MayChooseOneAbility=MagicMock(),
        )
        effect = SimpleNamespace()

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=MagicMock(),
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="",
        ):
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_not_called()

    def test_aoa_expert_campaign_with_remaining_health_offers_heal(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=MagicMock()),
            MayChooseOneAbility=MagicMock(),
        )
        effect = SimpleNamespace(this=MagicMock())

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=MagicMock(),
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="4",
        ):
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_called_once()

    def test_aoa_zero_remaining_hp_rejoins_at_mission_threat_cost(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        identity = MagicMock()
        identity.max_health = 12
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
            MayChooseOneAbility=MagicMock(),
        )
        mission = MagicMock()
        source = MagicMock()
        effect = SimpleNamespace(this=source)

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=mission,
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="0",
        ):
            ability.operation(effect, SimpleNamespace())

        source.PlaceThreatOnSchemes.assert_called_once_with([mission], 3, effect)
        identity.SetHealth.assert_called_once_with(12, effect)
        player.MayChooseOneAbility.assert_not_called()

    def test_aoa_expert_remaining_hp_is_capped_at_current_maximum(self):
        ability = ExpertCampaignSetPlayersHPToTheirRemainingHP()
        identity = MagicMock()
        identity.max_health = 10
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
        )
        effect = SimpleNamespace()

        with patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="12",
        ):
            ability.operation(effect, SimpleNamespace())

        identity.SetHealth.assert_called_once_with(10, effect)

    def test_aoa_standard_campaign_does_not_apply_remaining_hp(self):
        ability = ExpertCampaignSetPlayersHPToTheirRemainingHP()
        identity = MagicMock()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
        )

        with patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=False,
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ):
            ability.operation(SimpleNamespace(), SimpleNamespace())

        identity.SetHealth.assert_not_called()

    def test_aoa_heal_places_three_threat_before_healing_to_full(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        mission = MagicMock()
        identity = MagicMock()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
            MayChooseOneAbility=MagicMock(),
        )
        source = MagicMock()
        effect = SimpleNamespace(this=source)

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=mission,
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="4",
        ):
            ability.operation(effect, SimpleNamespace())

        choice = player.MayChooseOneAbility.call_args.args[1]
        choice_effect = SimpleNamespace(
            targets=[identity],
            GetPaidResources=lambda: None,
        )
        choice.operation(choice_effect, SimpleNamespace())

        self.assertEqual(
            source.method_calls,
            [
                call.PlaceThreatOnSchemes([mission], 3, effect),
                call.HealthUnits([identity], "All", effect),
            ],
        )

    def test_declining_aoa_heal_changes_neither_threat_nor_health(self):
        ability = ExpertCampaignEachPlayerMayHealAtMissionThreatCost()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=MagicMock()),
            MayChooseOneAbility=MagicMock(),
        )
        source = MagicMock()
        effect = SimpleNamespace(this=source)

        with patch(
            "cards.pack.aoa.campaign_setup.GetMissionScheme",
            return_value=MagicMock(),
        ), patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            return_value=True,
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetStrInternal",
            return_value="4",
        ):
            ability.operation(effect, SimpleNamespace())

        player.MayChooseOneAbility.assert_called_once()
        source.PlaceThreatOnSchemes.assert_not_called()
        source.HealthUnits.assert_not_called()


if __name__ == "__main__":
    unittest.main()
