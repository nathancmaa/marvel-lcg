from . import *

# Innate Perception


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            thwart=1,
        ),
    ]
