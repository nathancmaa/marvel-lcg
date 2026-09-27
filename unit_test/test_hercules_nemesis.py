from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order


ROOT = Path(__file__).resolve().parents[1]


class TestHerculesNemesisRegistration(unittest.TestCase):

    def test_starter_includes_obligation_and_complete_nemesis_set(self):
        starter = json.loads((ROOT / "deck" / "starter" / "hercules.json").read_text())

        self.assertEqual(starter["obligations"], ["59035"])
        self.assertEqual(
            starter["nemesis_set"],
            ["59036", "59037", "59038", "59039", "59040"],
        )

    def test_only_ares_is_registered_as_hercules_nemesis_minion(self):
        cards = json.loads((ROOT / "data" / "cards.json").read_text())
        papers = {paper["card_id"]: paper for paper in cards["hercules"]}

        self.assertEqual(papers["59036"]["desc"]["Nemesis"], "Hercules")
        self.assertNotIn("Nemesis", papers["59037"]["desc"])
        self.assertEqual(papers["59037"]["desc"]["HP"], "6")
        for card_id in ("59036", "59037", "59038", "59039", "59040"):
            self.assertEqual(papers[card_id]["set_name"], "Hercules Nemesis")


class TestAppealToAthena(unittest.TestCase):

    def test_appeal_to_athena_requires_two_mental_resources(self):
        module = import_module("cards.pack.hercules.hercules.59035")
        spend_mental = module.GetAbilities()[1]

        cost = spend_mental.GetCost(None, [])

        self.assertEqual(cost.b, 2)
        self.assertEqual(cost.y, 0)

    def test_appeal_to_athena_makes_gift_count_zero(self):
        module = import_module("cards.pack.hercules")
        player = SimpleNamespace(
            obligations_area=SimpleNamespace(
                FindCard=MagicMock(return_value=object()),
            ),
            GetControlCards=MagicMock(return_value=[object(), object()]),
        )

        self.assertEqual(module.CountGifts(player), 0)
        player.GetControlCards.assert_not_called()


class TestHerculesNemesisAbilities(unittest.TestCase):

    def test_ares_deals_an_encounter_card_after_scheming(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59036")
        ability = module.GetAbilities()[0]
        player = MagicMock()
        ares = MagicMock()
        effect = SimpleNamespace(this=ares)
        message = SimpleNamespace(
            GetAgainstPlayer=MagicMock(return_value=player),
        )

        ability.operation(effect, message)

        player.DealEncounterCards.assert_called_once_with(1, effect)

    def test_lernean_hydra_offers_spend_or_heal_choice(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59037")
        ability = module.GetAbilities()[0]
        player = MagicMock()
        attacker = SimpleNamespace(GetControlByPlayer=MagicMock(return_value=player))
        hydra = MagicMock()
        hydra.CastTo.return_value = hydra
        effect = SimpleNamespace(this=hydra)

        ability.operation(effect, SimpleNamespace(attacker=attacker))

        args = player.ChooseAbilities.call_args.args
        self.assertIs(args[0], effect)
        self.assertEqual(len(args[1:]), 2)
        self.assertEqual(args[1].name, "Lernean Hydra heals 2 damage")
        self.assertFalse(args[1].NeedCost())
        self.assertEqual(args[2].name, "Spend a [physical] resource")
        self.assertEqual(args[2].GetCost(None, []).r, 1)
        self.assertNotIn("ForChoiceAbilityWithCost", args[2].func_names)

    def test_olympic_feud_counts_olympus_cards(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59038")
        ability = module.GetAbilities()[0]
        scheme = MagicMock()
        scheme.CastTo.return_value = scheme
        effect = SimpleNamespace(this=scheme)

        with patch.object(module.Worlds, "FindCardSizeOnField", return_value=3):
            ability.operation(effect, SimpleNamespace())

        scheme.PlaceThreatOnSchemes.assert_called_once_with([scheme], 3, effect)

    def test_ares_axe_discards_after_a_damage_free_attack(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59039")
        ability = module.GetAbilities()[1]
        axe = MagicMock()
        effect = SimpleNamespace(this=axe)

        no_damage = SimpleNamespace(damaged_targets=[])
        took_damage = SimpleNamespace(damaged_targets=[MagicMock()])

        self.assertTrue(ability.conditions[-1](effect, no_damage))
        self.assertFalse(ability.conditions[-1](effect, took_damage))

        with patch.object(module.Faces, "DiscardAll") as discard_all:
            ability.operation(effect, no_damage)

        discard_all.assert_called_once_with([axe], effect)

    def test_god_of_war_reveals_a_minion_when_none_attack(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59040")
        ability = module.GetAbilities()[0]
        player = MagicMock()
        minion = MagicMock()
        effect = SimpleNamespace(this=MagicMock())
        message = SimpleNamespace(GetToPlayer=MagicMock(return_value=player))
        no_attacks = SimpleNamespace(activated_cnt=0)

        with patch.object(module.Players, "ForEachPlayer", return_value=no_attacks), patch.object(
            module.Worlds,
            "DiscardEncounterCardsUntil",
            return_value=minion,
        ) as discard_until:
            ability.operation(effect, message)

        discard_until.assert_called_once_with(effect, card_type=module.Minion)
        minion.Reveal.assert_called_once_with(player, effect)

    def test_god_of_war_does_not_search_when_a_minion_attacks(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59040")
        ability = module.GetAbilities()[0]
        effect = SimpleNamespace(this=MagicMock())
        attacks = SimpleNamespace(activated_cnt=1)

        with patch.object(module.Players, "ForEachPlayer", return_value=attacks), patch.object(
            module.Worlds,
            "DiscardEncounterCardsUntil",
        ) as discard_until:
            ability.operation(effect, SimpleNamespace())

        discard_until.assert_not_called()

    def test_god_of_war_orders_attacks_even_against_alter_ego_players(self):
        module = import_module("cards.pack.hercules.hercules_nemesis.59040")
        ability = module.GetAbilities()[0]
        player = SimpleNamespace(IsAlterEgo=MagicMock(return_value=True))
        effect = SimpleNamespace(this=MagicMock())
        attacks = SimpleNamespace(activated_cnt=1)

        def run_for_player(by_effect, operation, result):
            self.assertIs(by_effect, effect)
            return operation(player)

        with patch.object(module.Players, "ForEachPlayer", side_effect=run_for_player), patch.object(
            module.Worlds.Enemies,
            "DoActivateAgainstYouInternal",
            return_value=attacks,
        ) as activate:
            ability.operation(effect, SimpleNamespace())

        activate.assert_called_once_with(
            effect,
            player,
            activate="Attack",
            include_minion="Engaged",
            include_villain=False,
        )
        player.IsAlterEgo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
