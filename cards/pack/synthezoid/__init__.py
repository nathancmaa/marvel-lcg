from cards.pack import *


# Read cooperatively throughout. The pack is written for two teams, each with a
# Leader; this fork plays the cooperative half, where the players have no
# Leader of their own (Worlds.GetYourTeamLeader returns None) and "the enemy
# leader" means the one they are fighting. The Civil War pack settled that
# reading first -- see cards/pack/cw -- and these follow it.


def EnemyLeader(effect: 'Effect') -> 'CardFace|None':
    """The Leader the players are up against."""
    return Worlds.GetEnemyLeader(effect)


DENSE = "Dense"
INTANGIBLE = "Intangible"


def FindMassForm(effect: 'Effect') -> 'CardFace|None':
    """Vision's mass form attachment, whichever side is showing.

    Found by name rather than by the Form attribute: Form belongs to a player's
    identity, and this is a two-sided attachment on an enemy.
    """
    for name in (DENSE, INTANGIBLE):
        face = Worlds.FindCardOnField(effect, name=name, card_type=Attachment)
        if face:
            return face
    return None


def MassFormIs(effect: 'Effect', name: str) -> bool:
    face = FindMassForm(effect)
    return bool(face and face.IsName(name))


def FlipMassForm(effect: 'Effect', to: str = "") -> bool:
    """Turn the mass form over, or to a named side.

    Returns whether it actually moved, which Density Control needs: it only
    discards itself if the flip happened.
    """
    face = FindMassForm(effect)
    if not face:
        return False
    if to and face.IsName(to):
        return False
    other = INTANGIBLE if face.IsName(DENSE) else DENSE
    return face.FlipTo(effect, name=to or other)


def DifferentCardTypes(faces: Sequence['CardFace']) -> int:
    """How many different card types are among these cards.

    Three cards off the top of a deck is three chances at the same type, and
    several cards in the pack pay out per distinct type rather than per card.
    """
    return len({type(face).__name__ for face in faces})
