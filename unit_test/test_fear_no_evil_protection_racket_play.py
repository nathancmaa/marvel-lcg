"""Protection Racket's player-area schemes in real games.

Hung Out to Dry and Pawn Shop Showdown react to cards entering play "in
this play area". A form change or a villain stage flips a card that is
already in play, and the Bullseye villain's attachments are in the villain's
area, so none of those may add threat.
"""

import unittest

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.headless import HeadlessDeviceManager
from unit_test.fne_headless import build_scene, initialize_database, play


FLIP = 'Puzzle.ChangeFormFor(0, "Identity")'


def play_scheme(scheme_id, commands, seed=3):
    """Play Protection Racket (Bullseye) as Spider-Man with ``scheme_id``."""

    def choose_scheme(prompt):
        if not any("Protection_Racket_main_scheme" in (option.get("name") or "") for option in prompt.options):
            return None
        world = Engine.game.world
        for option in prompt.options:
            for target in option.get("all_legal_targets", []):
                card = world.object_manager.card_dict.get(target)
                if card and card.face.paper.card_id.startswith(scheme_id):
                    return CommandDescriptor(HeadlessDeviceManager._DescriptorId(option), [str(target)], [])
        return None

    run = play(
        build_scene("protection_racket", "bullseye", ["spider_man"], seed),
        [*commands, "Puzzle.End()"],
        on_prompt=choose_scheme,
        render=False,
    )
    schemes = [face for face in run.world.FindCardsOnField() if face.paper.card_id == f"{scheme_id}b"]
    return run, schemes[0]


class HungOutToDryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_changing_form_does_not_count_as_entering_play(self):
        run, scheme = play_scheme("60136", [FLIP, FLIP, FLIP])
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(scheme.threat, 0)
        self.assertEqual(run.world.GetFirstPlayer().GetIdentity().GetLostHealth(), 0)

    def test_an_ally_entering_your_play_area_is_damaged_and_adds_threat(self):
        run, scheme = play_scheme("60136", [FLIP, 'Puzzle.PutIntoPlay("01002")'])
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(scheme.threat, 1)
        black_cat = [face for face in run.world.FindCardsOnField() if face.paper.card_id == "01002"][0]
        self.assertEqual(black_cat.GetLostHealth(), 1)


class PawnShopShowdownTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_attachments_on_the_bullseye_villain_add_no_threat(self):
        run, scheme = play_scheme(
            "60137",
            [FLIP, 'Puzzle.PutIntoPlay("60069")', 'Puzzle.PutIntoPlay("60070")'],
        )
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(scheme.threat, 0)

    def test_an_upgrade_in_your_play_area_adds_threat(self):
        run, scheme = play_scheme("60137", [FLIP, 'Puzzle.PutIntoPlay("01008")'])
        self.assertEqual(run.Exceptions(), [])
        self.assertEqual(scheme.threat, 1)


if __name__ == "__main__":
    unittest.main()
