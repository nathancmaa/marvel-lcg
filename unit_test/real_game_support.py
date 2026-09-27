"""Shared helpers for tests that play a real game headlessly.

A test gives a list of debug-console commands that set the table at the
first player turns (like a puzzle), then a ``choose`` callback that answers
every later prompt. The game runs through the real controller; nothing in
the engine is mocked. Not a test module itself (no ``test_`` prefix).
"""

import contextlib
import io
import unittest
from unittest.mock import patch

from engine import Engine  # noqa: F401 - project import order

from game.scene.replay.operation import CommandDescriptor
from game.test.harness import Fixture, build_fixture_scene, initialize_database, run_scene_with_devices
from game.test.headless import HeadlessDeviceManager
from game.world.world_render import WorldRender


class RealGameCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()

    @staticmethod
    def payment_effect_ids(option):
        effects = []
        for payment in (option.get("target_payment") or {}).values():
            for payment_entry in payment.get("payment", []):
                effects.extend(str(effect_id) for effect_id in payment_entry)
        return effects

    @staticmethod
    def choice(option, targets=None, resources=None):
        if targets is None:
            minimum = int(option.get("target_num_range", [0, 0])[0])
            targets = [
                target.get("id", target) if isinstance(target, dict) else target
                for target in list(option.get("all_legal_targets", []))[:minimum]
            ]
        return CommandDescriptor(
            str(option.get("choice_id") or option["id"]),
            [str(target) for target in targets],
            [str(resource) for resource in (resources or [])],
        )

    @staticmethod
    def default(prompt):
        return HeadlessDeviceManager._DefaultChoice(prompt)

    @staticmethod
    def debug(command):
        Engine.game.controller_manager.console.SetCommand(command, Engine.game.world)
        return CommandDescriptor()

    @staticmethod
    def option_for_card(prompt, face):
        return next(
            (option for option in prompt.options if option.get("bind_id") == face.card.object_id),
            None,
        )

    def run_game(self, heroes, setup, choose, *, scenario="rhino", seed=180001,
                 expert=False, schemes=None, max_prompts=400):
        """Play until ``choose`` returns None at a prompt.

        ``setup`` commands run, one per prompt, at the first player turns.
        Prompts before setup finishes are answered with the default choice.
        """
        scene = build_fixture_scene(Fixture(scenario, tuple(heroes), seed))
        # The setup commands use the debug console namespace (hero, puzzle,
        # Faces, ...), which the restricted puzzle console does not offer.
        scene.SetMetadataBool("is_puzzle", False)
        scene.campaign.expert = expert
        if schemes:
            scene.campaign.schemes = list(schemes)
        setup = list(setup)
        started = {"value": False}

        def provider(prompt):
            if len(devices.prompts) > max_prompts:
                raise AssertionError("Unexpected repeated prompt")
            if prompt.event_name == "WhenPlayerInTurn" and setup:
                started["value"] = True
                return self.debug(setup.pop(0))
            if not started["value"] and prompt.event_name != "WhenPlayerInTurn":
                return self.default(prompt)
            return choose(prompt)

        devices = HeadlessDeviceManager(choice_provider=provider)
        with (
            contextlib.redirect_stdout(io.StringIO()) if not getattr(self, "show_output", False) else contextlib.nullcontext(),
            patch.object(WorldRender, "ErrorOccurred") as errors,
            patch.object(Engine, "SaveCrash"),
        ):
            game = run_scene_with_devices(scene, devices)
        self.errors = [call.args[0][-3000:] if call.args else str(call) for call in errors.call_args_list]
        return game, devices

    def assertNoGameErrors(self):
        self.assertEqual(self.errors, [])
