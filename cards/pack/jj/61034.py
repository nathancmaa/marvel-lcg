from . import *

# Innate Aggression


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            attack=1,
        ),
    ]
