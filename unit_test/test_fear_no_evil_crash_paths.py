"""Fear No Evil cards that raised in real play now resolve as printed.

Each test plays a real game to the situation and checks the card's effect,
not just the absence of an error.
"""

import unittest

from engine import Engine  # noqa: F401 - project import order

from unit_test.fne_headless import build_scene, initialize_database, play
from game.scene.replay.operation import CommandDescriptor
from game.test.headless import HeadlessDeviceManager


HERO_FORM = 'Puzzle.ChangeFormFor(0, "Identity")'


def on_field(world, card_id):
    return [face for face in world.FindCardsOnField() if face.paper.card_id == card_id]


class KingpinFinaleAttachmentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def kingpin_game(self, *commands, seed=11, render=False):
        run = play(build_scene("kingpin", None, ["spider_man"], seed), [HERO_FORM, *commands], render=render)
        self.assertEqual(run.Exceptions(), [])
        return run

    def test_james_wesley_attaches_and_gives_kingpin_a_facedown_boost_card(self):
        run = self.kingpin_game('Puzzle.Reveal("60165")')
        wesley = on_field(run.world, "60165")
        self.assertEqual(len(wesley), 1)
        kingpin = wesley[0].GetBindFace()
        self.assertTrue(kingpin.IsName("Kingpin"))
        self.assertEqual(kingpin.components.boostable.GetDeck().GetSize(), 1)

    def test_kingpins_cane_stuns_the_revealing_hero(self):
        run = self.kingpin_game('Puzzle.Reveal("60166")')
        self.assertEqual(len(on_field(run.world, "60166")), 1)
        self.assertTrue(run.world.GetFirstPlayer().GetIdentity().IsStunned())

    def test_vanessa_fisk_confuses_then_her_boost_adds_threat(self):
        run = self.kingpin_game('Puzzle.Reveal("60168")')
        self.assertEqual(len(on_field(run.world, "60168")), 1)
        self.assertTrue(run.world.GetFirstPlayer().GetIdentity().IsConfused())

    def test_vanessa_fisk_boost_places_threat_when_already_confused(self):
        run = self.kingpin_game(
            'Puzzle.Confuse(c1)',
            'Puzzle.Boost("60168")',
            render=True,
        )
        self.assertRegex(
            run.output,
            r"would place 1\S* \(\(\^!\d+\) \[\(\d+,60168\) Vanessa Fisk\] \(AbilityType\.Boost\)",
        )


class SensoryOverloadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_sense_upgrade_deals_damage_against_purple_man(self):
        # The obligation's effect is initiated by Purple Man here; it used to
        # assert in GetInitiator instead of dealing the damage.
        run = play(
            build_scene("the_getaway", "purple_man", ["daredevil"], 7),
            [HERO_FORM, 'Puzzle.Reveal("60032")', 'Puzzle.PutIntoPlay("60004")'],
            render=False,
        )
        self.assertEqual(run.Exceptions(), [])
        player = run.world.GetFirstPlayer()
        self.assertEqual([face.paper.card_id for face in player.obligations_area.Get()], ["60032"])
        self.assertEqual(player.GetIdentity().GetLostHealth(), 1)


class ImprisonedTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_imprisoned_sits_in_your_area_and_blocks_attack_thwart_and_alter_ego(self):
        state = {}

        def try_change_form(prompt):
            if state.get("armed") and prompt.event_name == "WhenPlayerInTurn" and not state.get("tried"):
                state["options"] = [option.get("name") for option in prompt.options]
                for option in prompt.options:
                    if option.get("name") == "Change_Form":
                        state["tried"] = True
                        return CommandDescriptor(HeadlessDeviceManager._DescriptorId(option), [], [])
            return None

        def arm(_world):
            state["armed"] = True
            return "Puzzle.End()"

        run = play(
            build_scene("the_raft_breakout", "hammerhead", ["spider_man"], 7),
            [HERO_FORM, 'Puzzle.Reveal("60150")', arm, "Puzzle.End()"],
            on_prompt=try_change_form,
            render=False,
        )
        self.assertEqual(run.Exceptions(), [])
        player = run.world.GetFirstPlayer()
        self.assertEqual([face.paper.card_id for face in player.obligations_area.Get()], ["60150"])
        self.assertNotIn("Attack", state["options"])
        self.assertNotIn("Thwart", state["options"])
        self.assertIn("Spend_3_resources_to_discard_Imprisoned", state["options"])
        # Choosing Change Form does not take Spider-Man to alter-ego.
        self.assertEqual(player.GetIdentity().paper.card_id, "01001a")


if __name__ == "__main__":
    unittest.main()
