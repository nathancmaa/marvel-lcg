"""NeXt Evolution campaign: where Hope's damage from the last scenario goes
is chosen at setup (ported from the sdolle1775 fork, 61408ae).

Not ported: their change to Teleported Away's extra threat (one per
environment rather than per environment per player) is unconfirmed.
"""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.pack.next_evol.campaign import (
    CampaignSetup,
    ChoosePreviousHopeDamagePlacement,
)


class TestNextEvolutionCampaign(unittest.TestCase):

    def test_previous_hope_damage_uses_forced_startup_choice(self):
        hope = MagicMock()
        scheme = MagicMock()
        first_player = MagicMock()
        effect = SimpleNamespace(
            world=MagicMock(),
            this=MagicMock(),
        )
        ability = ChoosePreviousHopeDamagePlacement(3, "Teleported Away")

        def find_card(effect_arg, *, name, card_type):
            return hope if name == "Hope Summers" else scheme

        with patch(
            "game.operate.campaign_logs.CampaignLog.GetIntInternal",
            return_value=4,
        ) as get_damage, patch(
            "cards.pack.next_evol.campaign.Worlds.FindCardOnField",
            side_effect=find_card,
        ), patch(
            "cards.pack.next_evol.campaign.Worlds.GetFirstPlayer",
            return_value=first_player,
        ):
            ability.operation(effect, SimpleNamespace())

        get_damage.assert_called_once_with(
            "Scenario 3 Hope Summers Damage",
            effect,
        )
        choices = first_player.ChooseAbilities.call_args.args
        self.assertIs(choices[0], effect)
        self.assertEqual(
            [choice.name for choice in choices[1:]],
            [
                "Place 4 damage on Hope Summers",
                "Place 4 threat on Teleported Away",
            ],
        )

        choice_effect = SimpleNamespace(
            targets=[],
            GetPaidResources=MagicMock(),
        )
        choices[1].operation(choice_effect, SimpleNamespace())
        hope.TakeDamage.assert_called_once_with(effect.this, 4, effect)

        choices[2].operation(choice_effect, SimpleNamespace())
        effect.this.PlaceThreatOnSchemes.assert_called_once_with(
            [scheme],
            4,
            effect,
        )

    def test_zero_previous_hope_damage_does_not_prompt(self):
        effect = SimpleNamespace(
            world=MagicMock(),
            this=MagicMock(),
        )
        ability = ChoosePreviousHopeDamagePlacement(3, "Teleported Away")

        with patch(
            "game.operate.campaign_logs.CampaignLog.GetIntInternal",
            return_value=0,
        ), patch(
            "cards.pack.next_evol.campaign.Worlds.FindCardOnField",
        ) as find_card, patch(
            "cards.pack.next_evol.campaign.Worlds.GetFirstPlayer",
        ) as get_first_player:
            ability.operation(effect, SimpleNamespace())

        find_card.assert_not_called()
        get_first_player.assert_not_called()

    def test_scenarios_use_their_specific_hope_damage_destinations(self):
        with patch(
            "cards.pack.next_evol.campaign.ChoosePreviousHopeDamagePlacement",
            return_value=MagicMock(),
        ) as choose_placement:
            CampaignSetup(4)
            choose_placement.assert_called_once_with(3, "Teleported Away")

            choose_placement.reset_mock()
            CampaignSetup(5)
            choose_placement.assert_called_once_with(4, "Stryfe's Grasp")


class TestCollectionSearch(unittest.TestCase):
    """Search.Collection, which the NeXt and Wonder Man cards use."""

    @classmethod
    def setUpClass(cls):
        from game.test.harness import initialize_database
        initialize_database()

    def test_identity_specific_means_the_printed_hero_class(self):
        from game.card.face.card_type import Ally
        from game.operate.search import Search
        player = MagicMock()
        player.AskChoosePaper.side_effect = lambda paper_ids: paper_ids[0]
        effect = SimpleNamespace(world=MagicMock())
        with patch("game.card.factory.CardFactory.GenerateCard") as generate:
            face = Search.Collection(
                effect, player, card_type=Ally, card_class="IdentitySpecific")
        self.assertIs(face, generate.return_value.face)
        self.assertTrue(player.AskChoosePaper.call_args.args[0])

    def test_a_search_that_finds_nothing_returns_none_instead_of_crashing(self):
        from game.card.face.card_type import Ally
        from game.operate.search import Search
        player = MagicMock()
        effect = SimpleNamespace(world=MagicMock())
        face = Search.Collection(
            effect, player, card_type=Ally, check_fn=lambda paper: False)
        self.assertIsNone(face)
        player.AskChoosePaper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
