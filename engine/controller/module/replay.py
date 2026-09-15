from core import *
from engine.log import Log
from game.scene.replay import *
from game.world import *
from engine.config import ConfigVariables
from engine.controller import *

CATEGORY_NAME = "REPLAY"
DISABLE_CRC_ERROR_ASSERT    = ConfigVariables.Bool('disable_crc_error_assert', False)
CRC_IGNORE_IDS              = ConfigVariables.ListInt('crc_ignore_ids', [])

class InputModule:

    def __init__(self, manager: 'ControllerManager') -> None:
        self.replay_inputs: List['OperationDescriptor'] = []
        self.history_inputs: List['OperationDescriptor'] = []

        self.current_step_id = 0
        self.replay_step_id = 0

        self.is_updated = False

        self.calculated_crc: List[str] = []

        self.is_replay: bool = False

        # Set when a recorded choice was dropped as a misfit: the player's
        # answer in its place goes into the recording rather than over the
        # choice that was recorded after it.
        self.insert_on_next_push: bool = False

        self.break_on: List[int] = []

        self.manager = manager

    def Clean(self):
        self.replay_inputs = []
        self.history_inputs = []
        self.insert_on_next_push = False

        self.current_step_id = 0
        self.replay_step_id = 0
        self.is_updated = False
        self.calculated_crc = []

    def Clear(self):
        self.break_on = []

    def SetReplayInputs(self, inputs: List['OperationDescriptor']):
        self.replay_inputs = inputs
        self.insert_on_next_push = False

    def DropMisfit(self) -> bool:
        """Take the recorded choice at this step out of the recording.

        It did not fit the ask; left in, every Redo would trip over it
        again. The player's answer in its place is slotted in, and Redo
        goes on from the choice recorded after it.
        """
        if self.replay_step_id >= len(self.replay_inputs):
            return False
        del self.replay_inputs[self.replay_step_id]
        self.insert_on_next_push = True
        return True

    def SetIsReplay(self, replay: bool):
        self.is_replay = replay

    def SetBreakOn(self, break_on: List[int]):
        self.break_on = break_on

    def PrintStepID(self) -> str:
        from colorama import Fore, Style
        # replay_inputs_max_size = self.GetReplayOperationLen()
        # return f'{Fore.RED}#{Style.RESET_ALL}{self.current_step_id} ({controller_manager.last_turn_start_step_id} | {controller_manager.undo.last_step}) /{replay_inputs_max_size if replay_inputs_max_size > 0 else ""}'
        return f'{Fore.RED}(#{self.current_step_id} / {len(self.replay_inputs)}){Style.RESET_ALL}'

    ################################################################################
    #
    @staticmethod
    def SameChoice(a: 'OperationDescriptor', b: 'OperationDescriptor') -> bool:
        """The same option, targets and payment: a choice made over again."""
        return a.effect.id == b.effect.id and \
            list(a.effect.targets) == list(b.effect.targets) and \
            list(a.effect.resources) == list(b.effect.resources)

    def Push(self, operation: 'OperationDescriptor'):
        # A choice made where the recording already has one -- after an
        # undo. Made over again, the same as recorded, it leaves the rest of
        # the recording for Redo to carry on with. Made differently, the
        # game is on a new path, and what was recorded beyond this point
        # belongs to the old one: replayed, it stopped the next undo short
        # and fed Redo choices for a table that no longer existed. It goes.
        # A choice made in place of a recorded one that was dropped as a
        # misfit is slotted in, so the recording after it is kept.
        if self.insert_on_next_push:
            self.insert_on_next_push = False
            self.replay_inputs.insert(self.replay_step_id, operation)
        elif self.replay_step_id < len(self.replay_inputs):
            if self.SameChoice(self.replay_inputs[self.replay_step_id], operation):
                self.replay_inputs[self.replay_step_id] = operation
            else:
                del self.replay_inputs[self.replay_step_id:]
                self.replay_inputs.append(operation)
        self.history_inputs.append(operation)
        self.current_step_id += 1
        self.replay_step_id += 1

        if self.current_step_id in self.break_on:
            self.manager.skip.SetIsSkipping(False)

    def Pop(self):
        self.history_inputs.pop()
        self.current_step_id -= 1
        self.replay_step_id -= 1

    def GetReplayOperation(self, is_puzzle: bool, *, check_crc: bool=True) -> Tuple['OperationDescriptor|None', bool]:
        from engine import Engine
        self.is_updated = False

        if self.GetReplayOperationLen() > self.replay_step_id:
            replay_input = self.replay_inputs[self.replay_step_id]
            if is_puzzle or not check_crc:
                return replay_input, True
            # return replay_input

            # Check crc
            if replay_input.crc == "":
                Log.Warn(CATEGORY_NAME, "Miss CRC")
            if replay_input.crc and \
                self.calculated_crc[0] != replay_input.crc and \
                self.calculated_crc[1] != replay_input.crc and \
                self.calculated_crc[2] != replay_input.crc and \
                not Engine.game.controller_manager.console.debug_cmds:

                disable_assert = DISABLE_CRC_ERROR_ASSERT.value

                import ast
                da = ast.literal_eval(replay_input.crc)
                if self.manager.game.scene.version == '0.5.9.4':
                    db = ast.literal_eval(self.calculated_crc[1])
                else:
                    db = ast.literal_eval(self.calculated_crc[0])

                # Get the union of keys from both dictionaries
                all_keys = sorted(set(da) | set(db))

                diff_text = ""
                diff_ids: List[int] = []
                # Compare and print
                def get_text(num: int|None) -> str:
                    if num == None:
                        return '-'
                    # if num == 0:
                    #     return '0'
                    if num >= 0:
                        return str(num)
                    if num == -2:
                        return 'Hand'
                    if num == -3:
                        return 'Top'
                    if num == -4:
                        return 'Btm'
                    # This happens when a unit has negative health
                    # assert False
                    return str(num)
                def get_diff_text(a: int|None, b: int|None) -> str:
                    if a == None:
                        a = 0
                    if b == None:
                        b = 0
                    if a < 0 or b < 0:
                        return ''
                    if a == b:
                        return ''
                    return "{:+}".format(b-a)

                for key in all_keys:
                    a_value = da.get(key, None)
                    b_value = db.get(key, None)
                    if a_value != b_value:
                        diff_ids.append(key)
                        diff_text += "c{:<4}| {:<4} | {:<4} | {:<3}\n".format(
                            key,
                            get_text(a_value),
                            get_text(b_value),
                            get_diff_text(a_value, b_value),
                        )

                from game.test import Test
                if not disable_assert:
                    tip_info = f""" Key | Read | Curr | (#{self.current_step_id} / {len(self.replay_inputs)})
"""
                    if Test.IsInTesting():
                        Log.Assert(CATEGORY_NAME, f'{tip_info}{diff_text}')
                    else:
                        # In play, the table's state differing from the
                        # recording's is worth knowing and not worth
                        # stopping for: the recorded choice is still tried
                        # against the ask, and put to the player again if it
                        # no longer fits. Stopping here dropped the player
                        # wherever the first difference lay.
                        Log.Warn(CATEGORY_NAME, f'{tip_info}{diff_text}')

                if Engine.in_unit_test:
                    Engine.SaveCrash()
                if Test.IsInTesting():
                    # DebugBreak()
                    if not disable_assert:
                        from core.lib.beep import Beep
                        Beep.Warning()
                        return replay_input, False
                    pass
                # Outside the tests the recording goes on regardless; see above.
                return replay_input, True
            return replay_input, True
        else:
            return None, True

    def GetReplayOperationLen(self) -> int:
        return len(self.replay_inputs)

    def UpdateReplayStepId(self, diff: int):
        self.replay_step_id += diff
        self.is_updated = True

