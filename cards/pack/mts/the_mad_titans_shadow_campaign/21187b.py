from . import *


def GetAbilities() -> Sequence['Ability']:
    def norn_stone(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.HealthUnits(effect.targets, 1, effect)

    return [
        *AbilityFactory.GiveKeywordToAttached(
            Hero,
            thwart=1,
            attack=1,
            defense=1,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            norn_stone,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget("YourIdentity", canbe_heal=True),
    ]
