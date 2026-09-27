"""Hercules's cards and nemesis set in real headless games."""

import unittest

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database
from unit_test.script_driver import Act, card_ids, object_id, on_field, play_script


def hand_id(card_id):
    def find(world):
        for face in world.GetFirstPlayer().hand_cards.Get():
            if face.paper.card_id == card_id:
                return face.card.object_id
        raise AssertionError(f"{card_id} is not in hand")
    return find


def hercules(world):
    return world.GetFirstPlayer().GetIdentity()


def rhino_fixture(*commands):
    return Fixture("rhino", ("hercules",), 777, ('Puzzle.ClearHand()', *commands))


HERO_FORM = 'Puzzle.ChangeForm("Hercules", "Hero")'


class InGameTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def assertCleanGame(self, devices):
        self.assertEqual(devices.errors, [])
        self.assertEqual(devices.unplayed_steps, [])
        self.assertNotIn("<E>", devices.output)


class HerculesCardsInGameTests(InGameTestCase):

    def test_son_of_zeus_readies_hercules_and_an_identity_specific_upgrade(self):
        game, devices = play_script(rhino_fixture(
            'Puzzle.CreateHandCards("59010", "59018", "59018")',
            HERO_FORM,
            'Puzzle.PutIntoPlay("59005")',
            'Puzzle.PutIntoPlay("59013")',
            'Puzzle.Exhaust("Hercules", "Gauntlets of Hercules")',
        ), [Act("Play", hand_id("59010"), payments=2)])

        self.assertCleanGame(devices)
        self.assertTrue(hercules(game.world).IsReady())
        self.assertTrue(on_field(game.world, "59013")[0].IsReady())

    def test_olympus_pays_for_a_card_by_exhausting_once(self):
        game, devices = play_script(rhino_fixture(
            HERO_FORM,
            'Puzzle.PutIntoPlay("59005")',
            'Puzzle.PutIntoPlay("59012")',
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("59014")',
        ), [Act("Play", hand_id("59014"), pay_from=("59012",))])

        self.assertCleanGame(devices)
        self.assertTrue(on_field(game.world, "59014"))
        self.assertFalse(on_field(game.world, "59012")[0].IsReady())

    def test_gauntlets_give_retaliate_for_each_gift(self):
        game, devices = play_script(rhino_fixture(
            HERO_FORM,
            'Puzzle.PutIntoPlay("59005")',
            'Puzzle.PutIntoPlay("59013")',
        ), ['Puzzle.DoAttack("Rhino")'])

        self.assertCleanGame(devices)
        self.assertFalse(on_field(game.world, "59013")[0].IsReady())
        # One gift: retaliate 1 against Rhino's 14 hit points.
        self.assertEqual(on_field(game.world, "01094")[0].health, 13)

    def test_prince_of_power_heals_the_excess_damage(self):
        game, devices = play_script(rhino_fixture(
            HERO_FORM,
            'Puzzle.PutIntoPlay("59017")',
            'Puzzle.Damage("Hercules", 5)',
            # Hydra Bomber (2 hit points) deals Hercules 2 more as it arrives.
            'Puzzle.Reveal("01110")',
        ), [Act("Attack", 1, targets=lambda world: [object_id(world, "01110")])])

        self.assertCleanGame(devices)
        self.assertFalse(on_field(game.world, "01110"))
        # 14 - 5 - 2 = 7, then 3 damage into 2 hit points heals 1.
        self.assertEqual(hercules(game.world).health, 8)

    def test_ancient_rivalry_needs_thor_and_readies_both(self):
        without_thor, devices = play_script(rhino_fixture(
            'Puzzle.CreateHandCards("59026", "59018")',
            HERO_FORM,
        ), [])
        rivalry = hand_id("59026")(without_thor.world)
        self.assertNotIn(
            ("Play", rivalry),
            [(o.get("name"), o.get("bind_id")) for o in devices.stopped_prompt.options],
        )

        game, devices = play_script(rhino_fixture(
            'Puzzle.CreateHandCards("59026", "59018")',
            'Puzzle.CreatePlayerDiscardPile("59013")',
            HERO_FORM,
            'Puzzle.PutIntoPlay("59020")',
            'Puzzle.Exhaust("Hercules", "Thor")',
        ), [Act(
            "Play",
            hand_id("59026"),
            targets=lambda world: [hercules(world).card.object_id, object_id(world, "59020")],
            payments=1,
        )])

        self.assertCleanGame(devices)
        self.assertTrue(hercules(game.world).IsReady())
        self.assertTrue(on_field(game.world, "59020")[0].IsReady())
        self.assertIn("59013", card_ids(game.world.GetFirstPlayer().hand_cards.Get()))

    def test_defeating_the_hydra_completes_the_labor_and_resolves_atonement(self):
        def labor_id(world):
            labors = world.GetFirstPlayer().special_decks["hercules_labor"].Get()
            return next(face for face in labors if face.paper.card_id == "59002").card.object_id

        attack = Act("Attack", 1, targets=lambda world: [object_id(world, "01131")])
        game, devices = play_script(
            rhino_fixture(
                HERO_FORM,
                # Tiger Shark (6 printed hit points) is the minion it finds.
                'Puzzle.CreateEncounterDeck("01131")',
            ),
            [lambda world: f"Puzzle.Reveal({labor_id(world)})"]
            + [attack, 'Puzzle.Ready("Hercules")'] * 3
            + [attack],
        )

        self.assertCleanGame(devices)
        world = game.world
        player = world.GetFirstPlayer()
        self.assertFalse(on_field(world, "01131"))
        self.assertEqual(card_ids(world.victory_display.Get()), ["59002"])
        self.assertNotIn("59002", card_ids(player.special_decks["hercules_labor"].Get()))
        # Completing a Labor is forced: nobody is asked whether to do it.
        self.assertFalse([p for p in devices.prompts if "WhenUnitBeDefeated" in p.event_name])
        # Atonement: the top Gift enters play and Hercules readies.
        self.assertEqual(len(player.special_decks["hercules_gift"].Get()), 2)
        self.assertEqual(len([f for f in world.FindCardsOnField() if f.HasTrait("GIFT")]), 1)
        self.assertTrue(hercules(world).IsReady())


class HerculesNemesisInGameTests(InGameTestCase):

    def test_starter_deck_shuffles_in_the_obligation_and_sets_the_nemesis_aside(self):
        game, _ = play_script(rhino_fixture(), [])
        world = game.world
        villain = world.GetScenario().area_villain.Get()[0]

        self.assertIn("59035", card_ids(villain.encounter_deck.Get()))
        self.assertEqual(
            sorted(card_ids(world.GetFirstPlayer().set_aside_nemesis_sets.Get())),
            ["59036", "59037", "59038", "59039", "59040"],
        )

    def test_appeal_to_athena_counts_no_gifts_until_it_is_removed(self):
        game, devices = play_script(rhino_fixture(
            'Puzzle.CreateHandCards("59010", "59018", "59018")',
            HERO_FORM,
            'Puzzle.PutIntoPlay("59005")',
            'Puzzle.PutIntoPlay("59013")',
            'Puzzle.Reveal("Appeal to Athena")',
            'Puzzle.Exhaust("Hercules", "Gauntlets of Hercules")',
        ), [Act("Play", hand_id("59010"), payments=2)])

        self.assertCleanGame(devices)
        self.assertEqual(card_ids(game.world.GetFirstPlayer().obligations_area.Get()), ["59035"])
        self.assertTrue(hercules(game.world).IsReady())
        # With no gifts counted, Son of Zeus readies no upgrade.
        self.assertFalse(on_field(game.world, "59013")[0].IsReady())

        game, devices = play_script(rhino_fixture(
            'Puzzle.Reveal("Appeal to Athena")',
        ), [Act("Alter-Ego_Action", lambda world: object_id(world, "59035"))])

        self.assertCleanGame(devices)
        self.assertEqual(card_ids(game.world.GetFirstPlayer().obligations_area.Get()), [])
        self.assertFalse(hercules(game.world).IsReady())

    def test_god_of_war_makes_ares_attack_hercules_in_alter_ego_form(self):
        game, devices = play_script(rhino_fixture(
            'Puzzle.Reveal("Ares")',
            'Puzzle.Reveal("God of War")',
        ), [])

        self.assertCleanGame(devices)
        self.assertEqual(hercules(game.world).paper.card_id, "59001b")
        # Ares attacks for 3 plus his boost card.
        self.assertLessEqual(hercules(game.world).health, 11)


if __name__ == "__main__":
    unittest.main()
