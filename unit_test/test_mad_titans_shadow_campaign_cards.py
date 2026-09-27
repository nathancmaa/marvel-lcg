"""Mad Titan's Shadow campaign cards (ported from the sdolle1775 fork, 08383e3):
Norn Stone keeps its stat bonus on its Recovery side, and Retrieve Odin's
Armor flips Odin to his KING side.
"""

import json
from importlib import import_module
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, sentinel

from engine import Engine  # noqa: F401 - establishes the project's import order


class TestNornStone(unittest.TestCase):

    project_root = Path(__file__).resolve().parents[1]

    def test_both_faces_grant_the_same_hero_stat_bonus(self):
        for card_id in ("21187a", "21187b"):
            with self.subTest(card_id=card_id):
                module = import_module(
                    "cards.pack.mts.the_mad_titans_shadow_campaign."
                    f"{card_id}"
                )
                with patch.object(
                    module.AbilityFactory,
                    "GiveKeywordToAttached",
                    return_value=[sentinel.stat_bonus],
                ) as give_stat_bonus:
                    abilities = module.GetAbilities()

                give_stat_bonus.assert_called_once_with(
                    module.Hero,
                    thwart=1,
                    attack=1,
                    defense=1,
                )
                self.assertIn(sentinel.stat_bonus, abilities)

    def test_recovery_face_displays_the_stat_bonus(self):
        cards_by_pack = json.loads(
            (self.project_root / "data" / "cards.json").read_text(
                encoding="utf-8"
            )
        )
        recovery_face = next(
            card
            for cards in cards_by_pack.values()
            if isinstance(cards, list)
            for card in cards
            if card.get("card_id") == "21187b"
        )

        self.assertIn(
            "Your hero gets +1 THW, +1 ATK, and +1 DEF.",
            recovery_face["text"],
        )



class TestRetrieveOdinsArmor(unittest.TestCase):

    def test_heals_odin_and_flips_him_to_king_side(self):
        module = import_module(
            "cards.pack.mts.the_mad_titans_shadow_campaign.21186b"
        )
        retrieve_odins_armor = module.GetAbilities()[1]

        effect = Mock()
        message = Mock()
        odin = Mock()
        odin.HasTrait.return_value = False

        with patch.object(
            module.Worlds,
            "FindCardOnField",
            return_value=odin,
        ):
            retrieve_odins_armor.operation(effect, message)

        effect.this.HealthUnits.assert_called_once_with(
            [odin],
            "All",
            effect,
        )
        odin.FlipTo.assert_called_once_with(effect, trait="KING")



if __name__ == "__main__":
    unittest.main()
