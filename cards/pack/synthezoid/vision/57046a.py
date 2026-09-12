from . import *

# Dense


def GetAbilities() -> Sequence['Ability']:
    # Nothing but the stat line and the side it is showing. Dense is what the
    # rest of the set reads when it wants him solid.
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Vision", card_type=Leader),
        ),
    ]
