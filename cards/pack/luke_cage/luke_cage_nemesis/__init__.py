from cards.pack.luke_cage import *


def FindLukeCagePlayer(effect: 'Effect') -> 'Player|None':
    """The seat playing Luke Cage.

    His nemesis set names him rather than "you", and in two-handed play the
    other seat can be the one turning the card over.
    """
    luke = FindLukeCage(effect)
    if not luke:
        return None
    owner = luke.GetOwner()
    return owner if Player.IsType(owner) else None
