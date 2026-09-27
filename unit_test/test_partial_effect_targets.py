from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
import game.card.card_finder.checker as card_finder_checker


def identity_matches(finder, *, can_heal=False, status=None):
    face = SimpleNamespace(
        CanHeath=MagicMock(return_value=can_heal),
        IsConfused=MagicMock(return_value=status == "Confused"),
        IsStunned=MagicMock(return_value=status == "Stunned"),
        IsTough=MagicMock(return_value=status == "Tough"),
    )
    with patch.object(card_finder_checker.Unit2, "IsType", return_value=True):
        return finder.Check(face)


class TestGodlikeStamina(unittest.TestCase):

    def test_action_can_heal_or_discard_a_status(self):
        ability = import_module("cards.pack.valk.25024").GetAbilities()[0]
        finder = ability.selectors[0].selector_filter.finder

        self.assertTrue(identity_matches(finder, can_heal=True))
        self.assertTrue(identity_matches(finder, status="Confused"))
        self.assertTrue(identity_matches(finder, status="Stunned"))
        self.assertTrue(identity_matches(finder, status="Tough"))
        self.assertFalse(identity_matches(finder))


class TestDrSinclair(unittest.TestCase):

    def setUp(self):
        self.module = import_module("cards.pack.silk.52017")
        self.ability = self.module.GetAbilities()[0]

    def test_action_can_heal_or_discard_a_status(self):
        finder = self.ability.selectors[0].selector_filter.finder

        self.assertTrue(identity_matches(finder, can_heal=True))
        self.assertTrue(identity_matches(finder, status="Confused"))
        self.assertFalse(identity_matches(finder))

    def test_status_discard_is_optional(self):
        support = MagicMock()
        identity = MagicMock()
        identity.recover = 4
        initiator = MagicMock()
        initiator.GetAlterEgo.return_value = identity
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=MagicMock(return_value=support)),
            GetInitiator=MagicMock(return_value=initiator),
            targets=[identity],
        )

        self.ability.operation(effect, SimpleNamespace())

        support.HealthUnits.assert_called_once_with([identity], 4, effect)
        initiator.MayChooseOneAbility.assert_called_once()
        initiator.ChooseAbilities.assert_not_called()


if __name__ == "__main__":
    unittest.main()
