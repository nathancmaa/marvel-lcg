"""Run real games headlessly for integration tests.

Pairs with ``game.test.headless``: a test builds a scene (a scenario, heroes,
a seed and puzzle commands that place exact cards), runs it through the real
controller with a ``HeadlessDeviceManager``, and inspects the world or the
prompts the UI would have been sent. Nothing is mocked; cards, messages,
effects and replay conversion all run as they do in a web game.

Adapted from the sdolle1775 fork's timing harness, less its timing labs and
legacy-rule checks: Rules Reference 1.8 is the only rules model here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from engine import Engine  # noqa: F401 - establishes project import order
from cards.database import CardsDB
from engine.lib import Json, Ver
from game.scene import Scene, SceneLoader


RULES = ["v18_all"]


class HeadlessStatistics:
    """Minimal statistics sink a real ``Game`` needs."""

    def CanRegisterAbility(self) -> bool:
        return True

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


@dataclass(frozen=True)
class Fixture:
    """A deterministic table: scenario, heroes, seed and puzzle commands."""

    scenario: str
    heroes: tuple[str, ...]
    seed: int
    commands: tuple[str, ...] = ()
    title: str = ""


def initialize_database() -> None:
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


def build_fixture_scene(fixture: Fixture) -> Scene:
    scene = SceneLoader.NewScene(
        fixture.scenario,
        None,
        list(fixture.heroes),
        fixture.seed,
    )
    scene.rules = list(RULES)
    scene.SetMetadataBool("is_puzzle", True)
    scene.SetMetadataStr("comment", fixture.title)
    scene.puzzle = list(fixture.commands)
    scene.inputs = []
    return scene


def validate_file(path: Path) -> Scene:
    """Load a recorded scene, requiring a good checksum and ``v18_all``."""
    scene, checksum = Json.LoadAsInternal(str(path), Scene, check_sum="Restrict")
    if checksum != "Ok":
        raise AssertionError(f"{path.name}: checksum={checksum}")
    if "v18_all" not in scene.rules:
        raise AssertionError(f"{path.name}: not a v18_all recording")
    return scene


def run_scene_with_devices(scene: Scene, devices, *, load_type: str = "New"):
    """Run an in-memory scene through the real game and device workflow."""
    from game.game import Game
    from game.test import Test
    from engine.job import JobManager

    initialize_database()
    if not hasattr(JobManager, "condition"):
        JobManager.Initialize()
    statistics = HeadlessStatistics()
    game = Game(statistics, devices)
    Engine.statistics = statistics
    Engine.game = game

    was_testing = Test.is_in_test
    Test.is_in_test = True
    try:
        game.session.SetScene(scene, load_type)
        game.GameSetup()
        game.GameLoop()
    finally:
        Test.is_in_test = was_testing

    return game


def run_fixture(fixture: Fixture, devices):
    """Start a fresh game from a fixture and play it with ``devices``."""
    return run_scene_with_devices(build_fixture_scene(fixture), devices)


def run_file_with_devices(path: Path, devices):
    """Fast-forward a recorded scene, then hand the table to ``devices``."""
    scene = validate_file(path)
    return run_scene_with_devices(scene, devices, load_type="InTesting")


def run_fixture_to_prompt(
    fixture: Fixture,
    *,
    event_name: str = "WhenPlayerInTurn",
    choices: Sequence = (),
):
    """Play a fixture to the first prompt whose event name matches.

    Returns the game, whose world stays available for assertions, and the
    device manager holding every prompt seen and the one it stopped at.
    """
    from game.test.headless import HeadlessDeviceManager

    devices = HeadlessDeviceManager(
        choices,
        stop_when=lambda prompt: event_name in prompt.event_name,
    )
    game = run_fixture(fixture, devices)
    if devices.stopped_prompt is None:
        raise AssertionError(f"{fixture.scenario}: did not reach {event_name}")
    return game, devices
