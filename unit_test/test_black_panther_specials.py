from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from game.card.card_finder import CardFinder
import game.card.card_finder.checker as card_finder_checker
from game.card.face.attribute.can_health import CanHealth


def finder_matches(finder, *, sustained, can_gain_tough=False):
    face = SimpleNamespace(
        sustained=sustained,
        CanGainTough=MagicMock(return_value=can_gain_tough),
    )
    with patch.object(card_finder_checker.Unit2, "IsType", return_value=True):
        return finder.Check(face)


class TestSustainedCardFinder(unittest.TestCase):

    def test_sustained_true_means_any_amount_of_damage(self):
        finder = CardFinder(sustained=True)

        self.assertFalse(finder_matches(finder, sustained=0))
        self.assertTrue(finder_matches(finder, sustained=1))
        self.assertTrue(finder_matches(finder, sustained=3))

    def test_sustained_false_means_no_damage(self):
        finder = CardFinder(sustained=False)

        self.assertTrue(finder_matches(finder, sustained=0))
        self.assertFalse(finder_matches(finder, sustained=1))


class TestKimoyoBeads(unittest.TestCase):

    def test_special_can_resolve_from_threat_or_a_confusable_enemy(self):
        ability = import_module(
            "cards.pack.bp.black_panther_shuri.51010"
        ).GetAbilities()[0]
        scheme_selector, enemy_selector = ability.selectors

        self.assertTrue(scheme_selector.selector_filter.finder.has_threat)
        self.assertTrue(enemy_selector.is_optional)
        self.assertTrue(enemy_selector.selector_filter.finder.canbe_confused)


class TestGoingUndercover(unittest.TestCase):

    def setUp(self):
        self.module = import_module("cards.pack.bp.51016")
        self.ability = self.module.GetAbilities()[0]
        self.player = MagicMock()
        self.effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=MagicMock()),
        )
        self.message = SimpleNamespace(
            GetDefeatingPlayer=MagicMock(return_value=self.player),
        )
        self.scenario_card = MagicMock()
        self.eligible_card = MagicMock()
        self.other_scenario_card = MagicMock()
        self.faces = [
            self.scenario_card,
            self.eligible_card,
            self.other_scenario_card,
        ]
        self.player.LookAtDeck.return_value = self.faces

    def resolve(self):
        with patch.object(
            self.module,
            "CardFinder",
        ) as finder_type, patch.object(
            self.module.Faces,
            "AddToVictoryDisplay",
        ) as add_to_victory:
            finder_type.return_value.Checks.return_value = [self.eligible_card]
            self.ability.operation(self.effect, self.message)
        return add_to_victory

    def test_player_may_decline_and_reorder_all_five_cards(self):
        self.player.MayChooseOneAbility.return_value = None

        add_to_victory = self.resolve()

        add_to_victory.assert_not_called()
        self.player.PlaceOnTopAndOrBottomInAnyOrder.assert_called_once_with(
            self.faces,
            self.effect,
        )

    def test_selected_card_goes_to_victory_and_only_the_rest_are_reordered(self):
        def choose_card(by_effect, choice):
            choice.operation(
                SimpleNamespace(
                    targets=[self.eligible_card],
                    GetPaidResources=MagicMock(),
                ),
                SimpleNamespace(),
            )
            return MagicMock()

        self.player.MayChooseOneAbility.side_effect = choose_card

        add_to_victory = self.resolve()

        add_to_victory.assert_called_once_with([self.eligible_card], self.effect)
        self.player.PlaceOnTopAndOrBottomInAnyOrder.assert_called_once_with(
            [self.scenario_card, self.other_scenario_card],
            self.effect,
        )


class TestWakandaForever(unittest.TestCase):

    def setUp(self):
        self.ability = import_module(
            "cards.pack.core.black_panther.01043a"
        ).GetAbilities()[0]

    def test_requires_every_black_panther_upgrade(self):
        selector = self.ability.selectors[0]
        upgrades = [MagicMock(), MagicMock(), MagicMock()]
        effect = MagicMock()

        self.assertEqual(selector.selector_range.raw_range, "All")
        self.assertEqual(selector.selector_range.GetTargetMin(effect, upgrades), 3)
        self.assertEqual(selector.selector_range.GetTargetMax(effect, upgrades), 3)

    def test_resolves_specials_in_selected_order(self):
        upgrades = [MagicMock(), MagicMock(), MagicMock()]
        initiator = MagicMock()
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=MagicMock()),
            GetInitiator=MagicMock(return_value=initiator),
            targets=upgrades,
        )

        self.ability.operation(effect, SimpleNamespace())

        initiator.ResolveSpecialAbility.assert_called_once_with(upgrades, effect)


class TestShuriVibraniumSuit(unittest.TestCase):

    def setUp(self):
        self.module = import_module("cards.pack.bp.black_panther_shuri.51013")
        self.ability = self.module.GetAbilities()[0]

    def test_special_requires_an_enemy_and_either_damage_or_tough(self):
        enemy_selector, hero_selector = self.ability.selectors
        hero_finder = hero_selector.selector_filter.finder

        self.assertFalse(enemy_selector.is_optional)
        self.assertFalse(hero_selector.is_optional)
        self.assertTrue(
            finder_matches(hero_finder, sustained=2, can_gain_tough=False)
        )
        self.assertTrue(
            finder_matches(hero_finder, sustained=0, can_gain_tough=True)
        )
        self.assertFalse(
            finder_matches(hero_finder, sustained=0, can_gain_tough=False)
        )

    def test_discard_choice_is_hidden_when_hero_cannot_gain_tough(self):
        hero = MagicMock()
        enemy = MagicMock()
        initiator = MagicMock()
        initiator.GetHero.return_value = hero
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=MagicMock()),
            GetInitiator=MagicMock(return_value=initiator),
            targets=[enemy],
        )

        self.ability.operation(effect, SimpleNamespace())

        choice = initiator.MayChooseOneAbility.call_args.args[1]
        self.assertTrue(choice.selectors[0].selector_filter.finder.canbe_tough)


class TestCoreVibraniumSuit(unittest.TestCase):

    def test_special_requires_a_damaged_hero(self):
        ability = import_module(
            "cards.pack.core.black_panther.01049"
        ).GetAbilities()[0]
        enemy_selector, hero_selector = ability.selectors

        self.assertFalse(enemy_selector.is_optional)
        self.assertFalse(hero_selector.is_optional)
        self.assertFalse(
            finder_matches(hero_selector.selector_filter.finder, sustained=0)
        )
        self.assertTrue(
            finder_matches(hero_selector.selector_filter.finder, sustained=2)
        )

    def test_moved_attack_damage_uses_the_normal_damage_pipeline(self):
        source = MagicMock()
        source.GetLostHealth.return_value = 1
        target = MagicMock()
        effect = MagicMock()
        effect.ability.IsLabel.return_value = True

        CanHealth.MoveDamage(source, 1, target, effect)

        source.HealHealth.assert_called_once_with(1, effect)
        source.DealDamage.assert_called_once_with([target], 1, effect)
        target.TakeDamage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
