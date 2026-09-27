from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from game.element.resources import Resources


class TestRockPaperScissors(unittest.TestCase):

    def setUp(self):
        self.module = import_module("cards.pack.deadpool.44056")

    def test_each_resource_on_a_multi_resource_card_is_checked(self):
        self.assertTrue(
            self.module._is_beat(
                Resources.FromText("RY"),
                Resources.FromText("B"),
            )
        )

    def test_wild_beats_each_non_wild_resource_but_not_wild(self):
        for resource in ("R", "B", "Y"):
            with self.subTest(resource=resource):
                self.assertTrue(
                    self.module._is_beat(
                        Resources.FromText("G"),
                        Resources.FromText(resource),
                    )
                )

        self.assertFalse(
            self.module._is_beat(
                Resources.FromText("G"),
                Resources.FromText("G"),
            )
        )

    def test_non_winning_resource_pair_does_not_win(self):
        self.assertFalse(
            self.module._is_beat(
                Resources.FromText("R"),
                Resources.FromText("B"),
            )
        )

    def test_issue_39_adds_super_charged_to_hand(self):
        ability = self.module.GetAbilities()[0]
        stored_energy = MagicMock()
        super_charged = MagicMock()
        initiator = MagicMock()
        discard_cost = SimpleNamespace(
            return_discarded_cards=[super_charged],
        )
        cost_func = MagicMock()
        cost_func.Get.return_value = discard_cost
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=MagicMock()),
            GetInitiator=MagicMock(return_value=initiator),
            targets=[stored_energy],
            cost_func=cost_func,
        )

        with patch.object(
            self.module.FacesCounter,
            "GetPrintedResources",
            side_effect=[
                Resources.FromText("RY"),
                Resources.FromText("B"),
            ],
        ):
            ability.operation(effect, SimpleNamespace())

        initiator.GainCard.assert_called_once_with(super_charged, effect)


if __name__ == "__main__":
    unittest.main()
