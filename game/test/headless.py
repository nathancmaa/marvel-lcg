"""Headless real-game driver used by integration tests and fixture tools.

This is intentionally a device implementation instead of a mock event manager:
messages, cards, effects, rendering, replay conversion, and prompt construction all
run through the same controller code as a web game.  A caller may supply choices
or stop on a prompt and inspect the exact wire descriptors that the UI would see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from engine.device import InputDevice, OutputDevice
from engine.device.manager.base import AskOptionPayload, DeviceManager
from engine.lib import Json
from game.scene.replay.operation import CommandDescriptor


@dataclass(frozen=True)
class HeadlessPrompt:
    player_id: int
    event_name: str
    ability_type: str
    prompt_text: str
    show_cancel: bool
    options: tuple[dict, ...]

    @classmethod
    def FromPayload(cls, player_id: int, payload: AskOptionPayload) -> "HeadlessPrompt":
        options = Json.LoadsAs(payload.options_json, list)
        return cls(
            player_id,
            payload.event_name,
            payload.ability_type,
            payload.prompt_text,
            payload.show_cancel,
            tuple(options),
        )


ChoiceProvider = Callable[[HeadlessPrompt], CommandDescriptor | None]
StopPredicate = Callable[[HeadlessPrompt], bool]


class HeadlessDevice(OutputDevice, InputDevice):
    def IsConnect(self) -> bool:
        return True

    def IsSyncReady(self) -> bool:
        return True

    def IsInputReady(self) -> bool:
        self.manager.ProvideInput(self.player_id)
        return True

    def Render(self) -> None:
        return None


class HeadlessDeviceManager(DeviceManager):
    """Run the normal controller with deterministic, noninteractive choices."""

    def __init__(
        self,
        choices: Sequence[CommandDescriptor] = (),
        *,
        stop_when: StopPredicate | None = None,
        choice_provider: ChoiceProvider | None = None,
    ) -> None:
        super().__init__()
        self._choices = list(choices)
        self.stop_when = stop_when
        self.choice_provider = choice_provider
        self.prompts: list[HeadlessPrompt] = []
        self.stopped_prompt: HeadlessPrompt | None = None

    def CreateDevices(self, controller):
        device = HeadlessDevice(controller, self)
        return device, device

    @staticmethod
    def _DescriptorId(option: dict) -> str:
        choice_id = option.get("choice_id")
        return str(choice_id if choice_id not in (None, "") else option["id"])

    @staticmethod
    def _DefaultChoice(prompt: HeadlessPrompt) -> CommandDescriptor:
        if not prompt.options:
            return CommandDescriptor()

        # Setup prompts such as mulligan permit an empty target selection.  For
        # a mandatory target prompt, choose the first rendered legal targets.
        option = prompt.options[0]
        target_range = option.get("target_num_range", [0, 0])
        target_minimum = int(target_range[0]) if target_range else 0
        rendered_targets = option.get("all_legal_targets", [])
        target_ids = [
            str(target.get("id", target) if isinstance(target, dict) else target)
            for target in rendered_targets[:target_minimum]
        ]
        return CommandDescriptor(
            HeadlessDeviceManager._DescriptorId(option),
            target_ids,
            [],
        )

    def ProvideInput(self, player_id: int) -> None:
        payload = self.ask_options[player_id]
        prompt = HeadlessPrompt.FromPayload(player_id, payload)
        self.prompts.append(prompt)

        if self.stop_when and self.stop_when(prompt):
            self._StopAtPrompt(player_id, prompt, payload)
            return

        if self._choices:
            command = self._choices.pop(0)
        elif self.choice_provider:
            command = self.choice_provider(prompt)
            if command is None:
                self._StopAtPrompt(player_id, prompt, payload)
                return
        else:
            command = self._DefaultChoice(prompt)

        payload.input_json = Json.Dumps(command)
        if player_id in self.asking_players:
            self.asking_players.remove(player_id)

    def _StopAtPrompt(
        self,
        player_id: int,
        prompt: HeadlessPrompt,
        payload: AskOptionPayload,
    ) -> None:
        """Leave a valid prompt snapshot and end the headless game cleanly.

        Exceptions raised inside a game message are intentionally converted to
        user-visible game errors.  A test checkpoint therefore uses the normal
        game-exit path after capturing the prompt rather than throwing through
        the dispatcher.
        """
        self.stopped_prompt = prompt
        payload.input_json = "{}"
        controller = self.controllers[player_id]
        if controller.world:
            controller.world.game_over.SetExit()
