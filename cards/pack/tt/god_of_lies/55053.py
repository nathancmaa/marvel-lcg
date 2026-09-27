from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.Interrupt,
            Identity,
            lambda effect, message: message.PreventDamage(4, effect),
        ).SetCostFunc(
            CostFunc.Counter("This", 1, 'synergy'),
        ).AnyPlayerCanDoThis(),
    ]
