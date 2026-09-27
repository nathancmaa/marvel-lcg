"""Villain and minion Steady/Stalwart stats match the keywords in their text."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SteadyStalwartDataTests(unittest.TestCase):

    def test_keyword_stats_match_card_text(self):
        data = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
        mismatched = []
        for pack in data.values():
            if not isinstance(pack, list):
                continue
            for card in pack:
                if not isinstance(card, dict) or card.get("type") not in ("Villain", "Minion"):
                    continue
                text = re.sub("<[^>]+>", "", card.get("text", ""))
                for keyword in ("Steady", "Stalwart"):
                    in_text = bool(re.search(r"(^|\n|\. )" + keyword + r"\.", text))
                    in_stats = keyword in card.get("desc", {})
                    if in_text != in_stats:
                        mismatched.append((card["card_id"], keyword))
        self.assertEqual(mismatched, [])


if __name__ == "__main__":
    unittest.main()
