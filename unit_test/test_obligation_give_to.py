"""Every obligation names who receives it, and revealing one does not crash.

``Obligation.give_to`` asserts when the card data has no ``GiveTo`` field.
Synthezoid Vision's Spellcasting and Blood Debt lacked it, so revealing
either raised out of the game loop and, in release mode, ended the server.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.test.harness import Fixture, initialize_database, run_fixture_to_prompt


CARDS_JSON = Path(__file__).resolve().parent.parent / "data" / "cards.json"


class ObligationGiveToDataTests(unittest.TestCase):

    def test_every_obligation_has_give_to(self):
        with open(CARDS_JSON, encoding="utf-8") as file:
            data = json.load(file)

        cards = {}
        for value in data.values():
            if isinstance(value, list):
                for card in value:
                    if isinstance(card, dict) and "card_id" in card:
                        cards[card["card_id"]] = card

        def resolved(card):
            seen = set()
            while "desc" not in card and card.get("full_link") and \
                card["card_id"] not in seen:
                seen.add(card["card_id"])
                card = cards[card["full_link"]]
            return card

        missing = []
        for card_id, card in cards.items():
            source = resolved(card)
            if source.get("type") != "Obligation":
                continue
            if "GiveTo" not in source.get("desc", {}):
                missing.append(f'{card_id} {card.get("name")}')

        self.assertEqual(missing, [])


class ObligationRevealTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    def reveal(self, card_id):
        from game.world.world_render import WorldRender

        fixture = Fixture(
            "rhino",
            ("spider_man",),
            9,
            ('Puzzle.ClearHand()', f'Puzzle.Reveal("{card_id}")'),
        )
        with patch.object(WorldRender, "ErrorOccurred") as error, \
            contextlib.redirect_stdout(io.StringIO()):
            game, _ = run_fixture_to_prompt(fixture)
        self.assertEqual(error.call_count, 0)
        player = game.world.GetFirstPlayer()
        return [face.paper.card_id for face in player.obligations_area.Get()]

    def test_spellcasting_goes_to_the_revealing_player(self):
        self.assertEqual(self.reveal("57063"), ["57063"])

    def test_blood_debt_goes_to_the_revealing_player(self):
        self.assertEqual(self.reveal("57072"), ["57072"])


if __name__ == "__main__":
    unittest.main()
