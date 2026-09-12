from core import *

@dataclass
class FrameDescriptor:
    render_id           : int
    game_id             : int
    ask_players         : List[int]
    remaining_time      : float
    max_timeout         : float
    notify_texts        : List[str]
    debug_message       : str
    current_step_id     : int
    max_replay_step_id  : int
    player_id           : int
    total_players       : int
    # The full world state for `render_id`, or None when this client was
    # already sent it (an input prompt re-announces the same render).  Carrying
    # it here saves the browser a round trip per render, which is most of what
    # a render costs over a tunnel.
    world               : Any = None
    # is_skipping         : bool

