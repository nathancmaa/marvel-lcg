"""Real-game helpers for the Fear No Evil tests.

Builds an FNE scenario with a chosen underling the way Quick Game does (the
underling's villain and cards folded into the scenario), then plays it
through the headless device manager. A test feeds console commands on each
player turn and inspects the world, prompts and any card errors afterwards.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path
from typing import Callable, Iterable, List
from unittest import mock

from engine import Engine  # noqa: F401 - project import order

from game.scene import SceneLoader
from game.scene.replay.operation import CommandDescriptor
from game.test.harness import RULES, initialize_database, run_scene_with_devices
from game.test.headless import HeadlessDeviceManager, HeadlessPrompt


ROOT = Path(__file__).resolve().parents[1]


def build_scene(
    scenario_id: str,
    underling: str | None,
    heroes: Iterable[str],
    seed: int,
    *,
    puzzle: Iterable[str] = (),
):
    initialize_database()
    scenario = json.loads((ROOT / f"data/scenarios/{scenario_id}.json").read_text(encoding="utf-8"))
    if underling:
        und = json.loads((ROOT / f"data/encounter_sets/{underling}.json").read_text(encoding="utf-8"))
        scenario["villain"] = und["villain"]
        scenario["set_aside"] = scenario.get("set_aside", []) + und.get("set_aside", [])
        scenario["encounters"] = scenario.get("encounters", []) + und.get("encounters", [])
    sets = list(dict.fromkeys(scenario.get("encounter_sets", []) + scenario.get("modular_sets", [])))
    hero_texts = [(ROOT / f"deck/starter/{hero}.json").read_text(encoding="utf-8") for hero in heroes]
    scene = SceneLoader.NewFromJson(json.dumps(scenario), sets, hero_texts, seed, list(RULES), {})
    scene.SetMetadataBool("is_puzzle", True)
    scene.puzzle = list(puzzle)
    scene.inputs = []
    return scene


def console(command: str) -> CommandDescriptor:
    Engine.game.controller_manager.console.SetCommand(command, Engine.game.world)
    return CommandDescriptor()


def keep_alive(world) -> str:
    """A puzzle command that heals every identity and clears main schemes.

    Lets one game sweep many cards without the villain winning part way.
    """
    from game.card.face.card_type import MainScheme

    commands = []
    for player in world.const_players:
        identity = player.GetIdentity()
        commands.append(f"Puzzle.Heal(c{identity.card.object_id}, 99)")
    for face in world.FindCardsOnField(card_type=MainScheme):
        commands.append(f"Puzzle.SetThreat(c{face.card.object_id}, 0)")
    return "; ".join(commands) or "Puzzle.End()"


def default_choice(prompt: HeadlessPrompt) -> CommandDescriptor:
    return HeadlessDeviceManager._DefaultChoice(prompt)


class GameRun:
    """The finished game plus everything a test may want to assert on."""

    def __init__(self, game, devices, output: str, errors: List[str], commands_run: int):
        self.game = game
        self.world = game.world
        self.devices = devices
        self.raw_output = output
        self.output = re.sub(r"\x1b\[[0-9;]*m", "", output)
        self.errors = errors
        self.commands_run = commands_run
        self.marks: List[tuple] = []

    def Exceptions(self) -> List[str]:
        lines = [
            line for line in self.output.splitlines()
            if line.startswith("<F>")
            and re.search(r"(Error|Exception)\b", line)
            and "Traceback" not in line
        ]
        return lines + list(self.errors)

    def ExceptionsByCommand(self) -> List[tuple]:
        """(command, exceptions) for each console command that raised."""
        text = self.raw_output
        result = []
        bounds = list(self.marks) + [(None, len(self.errors), len(text))]
        for (command, err_start, out_start), (_, err_end, out_end) in zip(bounds, bounds[1:]):
            chunk = GameRun(self.game, self.devices, text[out_start:out_end], self.errors[err_start:err_end], 0)
            found = chunk.Exceptions()
            if found:
                result.append((command, found[:3], chunk.CardFrames()[-2:]))
        return result

    def CardFrames(self) -> List[str]:
        return [line.strip() for line in self.output.splitlines() if "cards/pack/" in line and "File" in line]


def play(
    scene,
    commands: Iterable[str],
    *,
    on_prompt: Callable[[HeadlessPrompt], CommandDescriptor | None] | None = None,
    stop_after_commands: bool = True,
    max_prompts: int = 1500,
    render: bool = True,
) -> GameRun:
    """Play ``scene``, issuing one console command per player turn prompt.

    Other prompts go to ``on_prompt`` (return None to fall through), then to
    Cancel when offered, then to the first legal option. The game stops at the
    first player-turn prompt after the last command. ``render=False`` skips
    building a table descriptor for every logged event, which is most of the
    run time when nothing inspects the rendered frames.
    """
    from game.world.world_render import WorldRender

    plan = list(commands)
    state = {"index": 0, "prompts": 0}
    errors: List[str] = []
    marks: List[tuple] = []
    output = io.StringIO()
    original = WorldRender.ErrorOccurred

    def record_error(self, info):
        errors.append(str(info))
        return original(self, info)

    def choose(prompt: HeadlessPrompt):
        state["prompts"] += 1
        if state["prompts"] > max_prompts:
            return None
        if on_prompt:
            chosen = on_prompt(prompt)
            if chosen is not None:
                return chosen
        if prompt.event_name == "WhenPlayerInTurn":
            if Engine.game.world.is_game_over:
                return None
            if state["index"] >= len(plan):
                return None if stop_after_commands else default_choice(prompt)
            command = plan[state["index"]]
            state["index"] += 1
            if callable(command):
                command = command(Engine.game.world)
            marks.append((command, len(errors), output.tell()))
            return console(command)
        if prompt.show_cancel:
            return CommandDescriptor()
        return default_choice(prompt)

    devices = HeadlessDeviceManager(choice_provider=choose)
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(WorldRender, "ErrorOccurred", record_error))
        stack.enter_context(mock.patch.object(Engine, "SaveCrash", lambda *a, **k: None, create=True))
        if not render:
            stack.enter_context(mock.patch.object(WorldRender, "Present", lambda *a, **k: None))
        stack.enter_context(contextlib.redirect_stdout(output))
        game = run_scene_with_devices(scene, devices)
    run = GameRun(game, devices, output.getvalue(), errors, state["index"])
    run.marks = marks
    return run
