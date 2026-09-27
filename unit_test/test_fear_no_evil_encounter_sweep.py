"""Every Fear No Evil encounter card can be revealed and boosted without errors.

A real game per encounter set, one hero: each card is revealed and then
boosted while the hero is in alter-ego form, then again after changing to
hero form, where each minion also attacks. Any exception a card script raises is collected; the test fails
listing the cards that raised. This catches the crash paths message mocks
missed (wrong callback arguments, missing message methods, attributes that
only exist on attack boosts).
"""

import json
import unittest
from collections import defaultdict

from engine import Engine  # noqa: F401 - project import order

from unit_test.fne_headless import ROOT, build_scene, keep_alive, play


FLIP = 'Puzzle.ChangeFormFor(0, "Identity")'
ENCOUNTER_TYPES = ("Treachery", "Attachment", "Minion", "SideScheme", "Environment", "Obligation")

# (scenario, underling) a set's cards are swept in, so the villain and
# scheme they name are on the table.
CONTEXT = {
    "Bullseye": ("the_getaway", "bullseye"),
    "Electro": ("the_getaway", "electro"),
    "Hammerhead": ("the_getaway", "hammerhead"),
    "Purple Man": ("the_getaway", "purple_man"),
    "Typhoid Mary": ("the_getaway", "typhoid_mary"),
    "Art Museum Heist": ("art_museum_heist", "bullseye"),
    "The Getaway": ("the_getaway", "bullseye"),
    "Protection Racket": ("protection_racket", "electro"),
    "The Raft Breakout": ("the_raft_breakout", "hammerhead"),
    "Stop the Presses!": ("stop_the_presses", "purple_man"),
    "Kingpin": ("kingpin", None),
    "Disasters": ("protection_racket", "bullseye"),
    "Tracksuit Mafia": ("protection_racket", "bullseye"),
    "Cops": ("art_museum_heist", "electro"),
    "The Owl": ("art_museum_heist", "hammerhead"),
    "Drive": ("the_getaway", "electro"),
    "Tombstone": ("kingpin", None),
    "Daredevil Nemesis": ("the_getaway", "bullseye"),
    "Echo Nemesis": ("the_getaway", "electro"),
}


def encounter_cards_by_set():
    cards = json.loads((ROOT / "data/cards.json").read_text(encoding="utf-8"))["fne"]
    by_set = defaultdict(list)
    for card in cards:
        if card.get("type") in ENCOUNTER_TYPES and card.get("set_name") in CONTEXT:
            if all(card["card_id"] != seen[0] for seen in by_set[card["set_name"]]):
                # Permanent cards start in play and cannot become boost cards.
                boostable = "Permanent" not in card.get("desc", {})
                by_set[card["set_name"]].append((card["card_id"], boostable, card["type"] == "Minion"))
    return by_set


def sweep_plan(cards):
    plan = []
    for form in ("alter-ego", "hero"):
        if form == "hero":
            plan.append(FLIP)
        for card_id, boostable, minion in cards:
            plan += [f'Puzzle.Reveal("{card_id}")', keep_alive]
            if minion and form == "hero":
                # Attack abilities (Mysterio, Proxima Midnight) only run here.
                plan += [f'Puzzle.DoAttack("{card_id}")', keep_alive]
            if boostable:
                plan += [f'Puzzle.Boost("{card_id}")', keep_alive]
    return plan


def sweep_set(set_name, cards, hero="spider_man", seed=4242):
    """Sweep a set, starting a fresh game whenever one ends early.

    Returns (command, exceptions, card frames) per command that raised.
    """
    scenario, underling = CONTEXT[set_name]
    plan = sweep_plan(cards)
    failures = []
    games = 0
    in_hero_form = False
    while plan and games < 12:
        games += 1
        commands = ([FLIP] if in_hero_form and plan[0] != FLIP else []) + plan
        run = play(build_scene(scenario, underling, [hero], seed + games), commands, render=False)
        failures += run.ExceptionsByCommand()
        issued = commands[:run.commands_run]
        in_hero_form = in_hero_form or FLIP in issued
        # Skip the command a game ended on; it was reported if it raised.
        done = max(run.commands_run - (len(commands) - len(plan)), 1)
        plan = plan[done:]
    return failures, games


class FearNoEvilEncounterSweepTests(unittest.TestCase):

    def test_every_encounter_card_reveals_and_boosts_cleanly(self):
        report = []
        for set_name, cards in encounter_cards_by_set().items():
            failures, _ = sweep_set(set_name, cards)
            for command, exceptions, frames in failures:
                report.append(f"{set_name}: {command}: {exceptions} {frames}")
        self.assertEqual(report, [], "\n".join(report))


if __name__ == "__main__":
    unittest.main()
