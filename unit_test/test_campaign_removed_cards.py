"""A card whose text removes it from the campaign writes that in the log.

Red Skull's tech upgrades ("discard this card and remove it from the
campaign log") and Mutant Genesis's role upgrades ("remove this card from
the game and the campaign pool") pay a RemoveFromCampaignLog cost, which
used to do nothing, so the card came back next scenario.
"""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order
from game.ability.cost_func import CostFunc
from game.operate.campaign_logs import CampaignLog


class Store:

    def __init__(self):
        self.dic = {}

    def HasKey(self, key):
        return key in self.dic

    def SetStr(self, key, value):
        self.dic[key] = value


def _effect(store, *, campaign=True):
    world = SimpleNamespace(
        store=store,
        rule=SimpleNamespace(mode_campaign=SimpleNamespace(val=campaign)),
    )
    return SimpleNamespace(world=world, this=None)


def _face(card_id, player_id=0):
    return SimpleNamespace(
        paper=SimpleNamespace(card_id=card_id),
        name=card_id,
        GetOwner=lambda: SimpleNamespace(player_id=player_id),
    )


def _pay(face, effect, player=None):
    cost = CostFunc.RemoveFromCampaignLog("This")
    effect.ability = SimpleNamespace(flags=SimpleNamespace(is_check_pay=False))
    cost.cost_legal_targets = [face]
    with patch("game.operate.store.Stores.HasKey",
               side_effect=lambda key, by_effect: by_effect.world.store.HasKey(key)), \
         patch("game.operate.store.Stores.GetStr",
               side_effect=lambda key, by_effect: by_effect.world.store.dic[key]):
        return cost.CommitCost(effect, player)


class CampaignRemovedCardTests(unittest.TestCase):

    def test_a_red_skull_tech_upgrade_is_marked_removed_for_its_owner(self):
        store = Store()
        self.assertTrue(_pay(_face("04157", player_id=2), _effect(store)))
        self.assertEqual(store.dic, {"Player 3 tech upgrade removed from campaign": "Yes"})
        self.assertIn(
            "Player 3 tech upgrade removed from campaign", CampaignLog.GetKnownKeys())

    def test_a_mutant_genesis_role_upgrade_joins_the_removed_list_once(self):
        store = Store()
        store.dic["Role Upgrades removed from campaign"] = "32180"
        effect = _effect(store)
        _pay(_face("32176"), effect)
        _pay(_face("32176"), effect)
        self.assertEqual(
            store.dic["Role Upgrades removed from campaign"], "32180;32176")

    def test_outside_a_campaign_nothing_is_written(self):
        store = Store()
        self.assertTrue(_pay(_face("04155"), _effect(store, campaign=False)))
        self.assertEqual(store.dic, {})


if __name__ == "__main__":
    unittest.main()
