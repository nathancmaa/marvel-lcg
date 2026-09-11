from . import *

# * Power Man


def GetAbilities() -> Sequence['Ability']:

    def power_man(effect: 'Effect', message: 'Message.AfterStatusDiscardFrom') -> None:
        effect.GetInitiator().DrawUp(1, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(),
        AbilityFactory.AfterStatusDiscardFrom(
            AbilityType.HeroResponse,
            CardFinder(name=LUKE_CAGE),
            "Tough",
            power_man,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
