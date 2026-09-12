from . import *

# Defensive Formation


def GetAbilities() -> Sequence['Ability']:

    def defensive_formation(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Faces.GiveStatus(effect.targets, "Tough", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            defensive_formation,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, BLOCK_COUNTER))
        .SetTarget(Ally, trait="DEFENDER", canbe_tough=True),
    ]
