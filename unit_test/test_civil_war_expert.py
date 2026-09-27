"""The Civil War leaders' expert scenarios set up in real headless games."""

import unittest

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database
from unit_test.script_driver import play_script


# Expert uses stages III and IV; stage III sets up like stage I.
EXPERTS = {
    "captain_america_expert": ("56139", "Cap's Shield"),
    "captain_marvel_expert": ("56094", "Energy Channel"),
    "iron_man_expert": ("56061", None),
    "spider_woman_expert": ("56170", "Finesse"),
}


class CivilWarExpertTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_each_expert_leader_starts_at_stage_three_with_its_setup(self):
        for scenario, (stage_three, attachment) in EXPERTS.items():
            with self.subTest(scenario=scenario):
                game, devices = play_script(
                    Fixture(scenario, ("spider_man",), 11),
                    ['Puzzle.Draw(0)'],
                )
                self.assertEqual(devices.errors, [])
                self.assertNotIn("<E>", devices.output)

                leader = game.world.GetScenario().area_villain.Get()[0]
                self.assertEqual(leader.paper.card_id, stage_three)
                attached = [a.paper for a in leader.GetAttachedAttachments()]
                self.assertTrue(attached)
                if attachment:
                    self.assertIn(attachment, [paper.name.lstrip("* ") for paper in attached])
                else:
                    # Iron Man's setup reveals one of his Tech attachments.
                    self.assertTrue(all(paper.set_name == "Iron Man" for paper in attached))


if __name__ == "__main__":
    unittest.main()
