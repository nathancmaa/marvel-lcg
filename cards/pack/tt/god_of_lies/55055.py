from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.DoGenerateResources(
            AbilityType.Resource,
            "This",
            res_fn=lambda effect, message: Resources("GG"),
        ),
        AbilityFactory.CanGenerateResources(
            AbilityType.Resource,
            Resources("GG"),
        ).SetCostFunc(
            CostFunc.Counter("This", 1, 'synergy'),
        ).AnyPlayerCanDoThis(),
    ]
