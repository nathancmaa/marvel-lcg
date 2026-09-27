"""Cards printed "Max 1 per player" carry MaxPerUnit, and a second copy can't be played."""

import contextlib
import io
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database, run_fixture_to_prompt


ROOT = Path(__file__).resolve().parents[1]
MAX_ONE_PER_PLAYER = re.compile(
    r"max 1 (?:(?:\[\[)?team(?:\]\])? card )?per player\b|max 1 team per player\b",
    re.IGNORECASE,
)
# Fear No Evil's Stand Alone (60054) is tracked with the FNE cards.
NOT_YET_ENCODED = {"60054"}


class MaxPerPlayerLimitTests(unittest.TestCase):

    def test_printed_max_one_per_player_limits_are_encoded(self):
        data = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
        missing = [
            (card["card_id"], card["name"])
            for pack in data.values() if isinstance(pack, list)
            for card in pack
            if isinstance(card, dict)
            and MAX_ONE_PER_PLAYER.search(card.get("text", ""))
            and card.get("desc", {}).get("MaxPerUnit") != "1"
            and card["card_id"] not in NOT_YET_ENCODED
        ]
        self.assertEqual(missing, [])


class SecondCopyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_a_second_children_of_the_atom_is_not_playable(self):
        from game.world.world_render import WorldRender

        fixture = Fixture("rhino", ("spider_man",), 5, (
            'Puzzle.ClearHand()',
            'Puzzle.CreateHandCards("49037", "49037", "01088")',
            'Puzzle.PutIntoPlay("49037")',
        ))
        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game, devices = run_fixture_to_prompt(fixture)

        self.assertEqual(error.call_count, 0)
        player = game.world.GetFirstPlayer()
        second = next(face for face in player.hand_cards.Get() if face.paper.card_id == "49037")
        self.assertFalse([option for option in devices.stopped_prompt.options
                          if option.get("bind_id") == second.card.object_id])


if __name__ == "__main__":
    unittest.main()
