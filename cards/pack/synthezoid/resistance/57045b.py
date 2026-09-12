from . import *

# Expose Overreach


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.CardsEnterPlayExhausted(
            Ally,
        ),
    ]
