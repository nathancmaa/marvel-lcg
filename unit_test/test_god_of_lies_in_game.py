"""Loki, God of Lies (Trickster Takeover) in real headless games."""

import unittest

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database
from unit_test.script_driver import Act, choose, on_field, play_script


def avatar(world):
    for villain in world.GetScenario().area_villain.Get():
        if villain.HasTrait("AVATAR OF LOKI"):
            return villain
    raise AssertionError("no Avatar of Loki in play")


def loki(world):
    faces = [f for f in world.FindCardsOnField() if f.paper.card_id in ("55027a", "55027b")]
    assert faces, "Loki, God of Lies is not in play"
    return faces[0]


def defeat_the_avatar(world):
    return f"Puzzle.Damage({avatar(world).card.object_id}, 40)"


class GodOfLiesInGameTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def assertCleanGame(self, devices):
        self.assertEqual(devices.errors, [])
        self.assertNotIn("<E>", devices.output)
        self.assertNotIn("<F>", devices.output)

    def play_to_the_win(self, scenario, heroes, seed):
        game, devices = play_script(
            Fixture(scenario, heroes, seed),
            [defeat_the_avatar] * 12,
        )
        self.assertCleanGame(devices)
        self.assertTrue(game.world.is_game_over)
        self.assertEqual(game.world.game_over.reason, "Players Won")
        # Each defeated Avatar shatters for 5 per hero into Loki's 20 per
        # hero, so the fourth defeat wins.
        self.assertEqual(len(devices.unplayed_steps), 8)

    def test_shattering_four_avatars_wins_in_standard(self):
        self.play_to_the_win("god_of_lies", ("spider_man",), 1)

    def test_shattering_four_avatars_wins_in_expert(self):
        self.play_to_the_win("god_of_lies_expert", ("hercules",), 6)

    def test_shattering_four_avatars_wins_two_handed(self):
        self.play_to_the_win("god_of_lies", ("captain_marvel", "hercules"), 41)

    def test_a_shattered_avatar_damages_loki_and_a_new_avatar_takes_its_place(self):
        game, devices = play_script(
            Fixture("god_of_lies", ("spider_man",), 1),
            [defeat_the_avatar],
        )
        world = game.world
        self.assertCleanGame(devices)
        self.assertEqual(loki(world).health, 15)
        new_avatar = avatar(world)
        self.assertEqual(new_avatar.paper.card_id[-1], "a")
        self.assertEqual(new_avatar.health, 15)
        self.assertEqual(new_avatar.GetCounters("shatter"), 0)

    def test_loki_two_gives_the_avatar_intense_focus_in_standard(self):
        game, devices = play_script(
            Fixture("god_of_lies", ("spider_man",), 1),
            [defeat_the_avatar] * 2,
        )
        world = game.world
        self.assertCleanGame(devices)
        self.assertEqual(loki(world).paper.card_id, "55027b")
        focus = [a.paper.card_id for a in avatar(world).GetAttachedAttachments()]
        self.assertIn("55034a", focus)
        # 15 hit points plus Intense Focus's 2 per hero.
        self.assertEqual(avatar(world).health, 17)

    def test_loki_two_flips_intense_focus_to_total_focus_in_expert(self):
        game, devices = play_script(
            Fixture("god_of_lies_expert", ("hercules",), 6),
            [defeat_the_avatar] * 2,
        )
        world = game.world
        self.assertCleanGame(devices)
        self.assertEqual(loki(world).paper.card_id, "55027b")
        focus = [a.paper.card_id for a in avatar(world).GetAttachedAttachments()]
        self.assertIn("55034b", focus)
        self.assertNotIn("55034a", focus)

    def test_stories_and_lies_swaps_the_avatar_and_keeps_its_damage(self):
        before = []

        def damage_the_avatar(world):
            before.append(avatar(world).paper.card_id)
            return f"Puzzle.Damage({avatar(world).card.object_id}, 5)"

        game, devices = play_script(
            Fixture("god_of_lies", ("spider_man",), 1),
            [damage_the_avatar, 'Puzzle.Reveal("Stories and Lies")'],
        )
        self.assertCleanGame(devices)
        swapped = avatar(game.world)
        self.assertNotEqual(swapped.paper.card_id, before[0])
        self.assertEqual(swapped.health, 10)

    def test_dark_scepter_is_discarded_by_spending_two_resources_of_a_type(self):
        def pay_for_the_scepter(prompt, world):
            scepters = [face.card.object_id for face in on_field(world, "55036")]
            for option in prompt.options:
                if option.get("bind_id") in scepters:
                    return choose(prompt, Act(None, option["bind_id"], payments=2), world)
            return None

        game, devices = play_script(
            Fixture("god_of_lies", ("hercules",), 4242, (
                'Puzzle.ClearHand()',
                'Puzzle.PutIntoPlay("55036")',
                'Puzzle.ChangeForm("Hercules", "Hero")',
                # Two cards with a printed [physical] resource.
                'Puzzle.CreateHandCards("59018", "59018")',
            )),
            ['Puzzle.Reveal("Dirty Trick")'],
            other=pay_for_the_scepter,
        )
        self.assertCleanGame(devices)
        self.assertFalse(on_field(game.world, "55036"))
        self.assertEqual(game.world.GetFirstPlayer().hand_cards.Get(), [])


if __name__ == "__main__":
    unittest.main()
