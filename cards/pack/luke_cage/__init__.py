from cards.pack import *


BURSTEIN_PROCESS = "Burstein Process"
LUKE_CAGE = "Luke Cage"

# Defensive Formation's uses. Registered in CardFace.COUNTER.
BLOCK_COUNTER = "block"


def FindLukeCage(effect: 'Effect') -> 'CardFace|None':
    """Luke Cage himself, in whichever form he is currently wearing.

    Most of the pack names him rather than saying "your identity", and the
    difference shows in two-handed play, where the other seat's cards are
    looking at a Luke Cage that is not their controller's identity.
    """
    return Worlds.FindCardOnField(effect, name=LUKE_CAGE, card_type=Identity)


def ToughOn(face: 'CardFace|None') -> int:
    """How many tough status cards a character is carrying.

    Everything in this pack counts them, and most of it counts them on Luke
    Cage, who is the one character in the game that can hold more than one.
    """
    return face.CastTo(CanStatus).tough if face and CanStatus.IsType(face) else 0
