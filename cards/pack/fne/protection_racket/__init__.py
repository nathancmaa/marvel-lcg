from cards.pack import *


PROTECTION_RACKET_SCHEMES = CardFinder(
    set_name="Protection Racket",
    card_type=MainScheme,
)


def GetSchemePlayer(effect: 'Effect') -> 'Player|None':
    """The player whose play area this Protection Racket scheme is in.

    The scheme is put into play for the first player but owned by the
    villain, so fall back to the player at the scheme's table.
    """
    this = effect.this
    owner = this.card.GetOwner()
    if isinstance(owner, Player):
        return owner
    for player in effect.world.const_players:
        if player.GetIdentity().card.game_area == this.card.game_area:
            return player
    return None


def IsInThisPlayArea(face: 'CardFace|None', effect: 'Effect') -> bool:
    """Whether ``face`` is in the play area of this scheme's player.

    Minions are there while engaged with that player; attachments are where
    the card they attach to is. The villain and its attachments are not.
    """
    player = GetSchemePlayer(effect)
    if player is None or face is None:
        return False
    if Minion.IsType(face):
        return face.CastTo(Minion).engaged_player == player
    if Attachment.IsType(face):
        attached_to = face.CastTo(Attachment).GetBindFace()
        return attached_to is not None and IsInThisPlayArea(attached_to, effect)
    play_area = face.card.area.play_area
    if play_area is not None:
        return play_area == player
    return face.GetControlBy() == player


def EnteredPlayFresh(message: 'Message.AfterCardEnterPlay') -> bool:
    """False when the "entering play" is a card turning over in play.

    A form change, or a villain moving to its next stage, flips a card that
    stays in play; "enters play" abilities must not fire for it.
    """
    if getattr(message.pre_message, "is_flip", False):
        return False
    return not message.from_area.flags.is_in_play


def PlaceThreatHere(effect: 'Effect', value: int=1) -> None:
    effect.this.CastTo(MainScheme).PlaceThreatOnSchemes([effect.this], value, effect)


def SelectProtectionRacketScheme(effect: 'Effect') -> None:
    """Resolve the printed solo setup choice for Protection Racket."""
    this = effect.this.CastTo(MainScheme)
    candidates = [this] + Worlds.MainSchemesDeck(effect).FindCards(
        PROTECTION_RACKET_SCHEMES,
    )
    if len(candidates) <= 1:
        return

    if Worlds.IsExpert(effect):
        chosen = Rand.RandomChoice(candidates, effect)
    else:
        chosen = Worlds.GetFirstPlayer(effect).AskChooseFace(
            candidates,
            effect,
            prompt="Choose your Protection Racket main scheme",
        )
    if not chosen:
        chosen = candidates[0]

    selected_current = chosen == this
    Faces.SetAside([candidate for candidate in candidates if candidate != chosen], effect)
    if chosen.paper.card_id.lower().endswith("a"):
        chosen.card.Flip(effect)
        chosen = chosen.card.face.CastTo(MainScheme)
    if not selected_current:
        chosen.PutIntoPlay("FirstPlayer", effect)


def SwapProtectionRacketScheme(effect: 'Effect') -> None:
    """Swap the active scheme with a random set-aside one and transfer threat."""
    current = Worlds.FindMainScheme(effect)
    candidates = Worlds.GetSetAsideAreaCards(effect, PROTECTION_RACKET_SCHEMES)
    if not current or not candidates:
        return

    chosen = Rand.RandomChoice(candidates, effect)
    threat = current.threat
    current.RemoveThreatInternal(effect.this, "All", effect)
    Faces.SetAside([current], effect)

    if chosen.paper.card_id.lower().endswith("a"):
        chosen.card.Flip(effect)
        chosen = chosen.card.face.CastTo(MainScheme)
    chosen.PutIntoPlay("FirstPlayer", effect)
    chosen.PlaceThreatOnSchemes([chosen], threat, effect)
