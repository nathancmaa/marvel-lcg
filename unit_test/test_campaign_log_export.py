from types import SimpleNamespace
import unittest

from engine import Engine  # noqa: F401 - establishes the project's import order
from game.operate.campaign_logs import CampaignLog


class CampaignStore:

    def __init__(self, values):
        self.dic = values

    def HasKey(self, key):
        return key in self.dic


class TestCampaignLogExport(unittest.TestCase):

    def test_exports_only_known_campaign_values(self):
        world = SimpleNamespace(
            store=CampaignStore({
                "Reputation Track": "7",
                "Role P1": "Defender",
                "temporary campaign setup flag": "1",
            }),
            const_players=[],
        )

        exported = CampaignLog.Export(world)

        self.assertEqual(exported["Reputation Track"], "7")
        self.assertEqual(exported["Role P1"], "Defender")
        self.assertNotIn("temporary campaign setup flag", exported)

    def test_records_remaining_hit_points_after_a_victory(self):
        identity = SimpleNamespace(health=6)
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=lambda: identity,
        )
        world = SimpleNamespace(
            store=CampaignStore({}),
            const_players=[player],
        )

        exported = CampaignLog.Export(
            world,
            include_remaining_hit_points=True,
        )

        self.assertEqual(exported["Player 1 Remaining hit points"], "6")

    def test_carries_unknown_keys_the_scenario_started_with(self):
        # A key an older build or the log editor recorded must not vanish
        # just because the engine does not list it.
        key = "Final Reputation Score: Victory for Scenario #5 - Venom Goblin"
        world = SimpleNamespace(
            store=CampaignStore({
                "Reputation Track": "7",
                key: "12",
                "temporary campaign setup flag": "1",
            }),
            const_players=[],
            scene=SimpleNamespace(campaign=SimpleNamespace(campaign_log={
                key: "10",
            })),
        )

        exported = CampaignLog.Export(world)

        self.assertEqual(exported[key], "12")
        self.assertNotIn("temporary campaign setup flag", exported)


if __name__ == "__main__":
    unittest.main()
