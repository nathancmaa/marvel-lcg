"""A small scripted driver for real headless games, shared by content tests.

At each of the player's turn prompts the driver takes the next step:

- a string, or a callable taking the world and returning a string, is a puzzle
  command (``Puzzle.Exhaust("Hercules")``) run through the debug console;
- a :class:`Act` picks an option from that prompt.

Every other prompt takes the first option with its minimum targets unless an
``other`` handler answers it. The game stops at the first turn prompt after the
last step, and the world stays available for assertions.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from typing import Callable

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import run_fixture
from game.test.headless import HeadlessDeviceManager


@dataclass
class Act:
    """Choose the option ``name`` of the card ``bind`` (object id or callable).

    A ``name`` of None takes any option of that card.
    ``payments`` pays with the first that many offered resources;
    ``pay_from`` pays with the resources of the named card ids instead.
    """

    name: str|None
    bind: int|Callable
    targets: list|Callable|None = None
    payments: int = 0
    pay_from: tuple[str, ...] = ()


def _resolve(value, world):
    return value(world) if callable(value) else value


def choose(prompt, act: Act, world) -> CommandDescriptor:
    bind = _resolve(act.bind, world)
    for option in prompt.options:
        if act.name in (None, option.get("name")) and option.get("bind_id") == bind:
            break
    else:
        raise AssertionError(
            f"no {act.name} option for {bind}: "
            f"{[(o.get('name'), o.get('bind_id')) for o in prompt.options]}"
        )

    targets = _resolve(act.targets, world)
    if targets is None:
        minimum = int((option.get("target_num_range") or [0])[0])
        targets = [
            target.get("id", target) if isinstance(target, dict) else target
            for target in option.get("all_legal_targets", [])[:minimum]
        ]
    payment_ids: list[str] = []
    payment = (option.get("target_payment") or {}).get("0", {}).get("payment", [])
    if act.pay_from:
        effects = world.object_manager.paying_effect_dict
        for entry in payment:
            for key in entry:
                if effects[int(key)].this.paper.card_id in act.pay_from:
                    payment_ids.append(str(key))
        if not payment_ids:
            raise AssertionError(
                f"no resource from {act.pay_from}: "
                f"{[(key, effects[int(key)].this.paper.card_id) for entry in payment for key in entry]}"
            )
    elif act.payments:
        for entry in payment[:act.payments]:
            payment_ids.extend(str(key) for key in entry)
    return CommandDescriptor(
        str(option["id"]),
        [str(target) for target in targets],
        payment_ids,
    )


def play_script(fixture, steps, *, other=None):
    """Play ``fixture`` through ``steps``; return the game and the devices."""
    queue = list(steps)
    errors: list[str] = []

    failures: list[BaseException] = []

    def provider(prompt):
        try:
            return answer(prompt)
        except Exception as exc:  # surfaced after the game stops
            failures.append(exc)
            return None

    def answer(prompt):
        if prompt.prompt_text and str(prompt.prompt_text).startswith("Error occurred"):
            errors.append(prompt.prompt_text)
            return None
        world = Engine.game.world
        if "WhenPlayerInTurn" in prompt.event_name:
            if not queue:
                return None
            step = queue.pop(0)
            if isinstance(step, Act):
                return choose(prompt, step, world)
            Engine.game.controller_manager.console.SetCommand(_resolve(step, world), world)
            return CommandDescriptor()
        if other:
            command = other(prompt, world)
            if command is not None:
                return command
        return HeadlessDeviceManager._DefaultChoice(prompt)

    devices = HeadlessDeviceManager(choice_provider=provider)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        game = run_fixture(fixture, devices)
    if failures:
        raise failures[0]
    devices.errors = errors
    devices.output = output.getvalue()
    devices.unplayed_steps = queue
    return game, devices


def card_ids(faces) -> list[str]:
    return [face.paper.card_id for face in faces]


def on_field(world, card_id: str):
    return [face for face in world.FindCardsOnField() if face.paper.card_id == card_id]


def object_id(world, card_id: str) -> int:
    faces = on_field(world, card_id)
    assert faces, f"{card_id} is not in play"
    return faces[0].card.object_id
