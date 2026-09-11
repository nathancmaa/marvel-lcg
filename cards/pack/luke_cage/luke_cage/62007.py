from . import *

# * Fogwell's Gym


def GetAbilities() -> Sequence['Ability']:

    def fogwells_gym(effect: 'Effect', message: 'Message.AfterStatusDiscardFrom') -> None:
        Faces.ReadyAll([message.trigger], effect)

    return [
        AbilityFactory.CanPlayThisSupportCard(),
        # Any DEFENDER, not only Luke Cage: the gym reads the trait, and this
        # pack puts that trait on most of its allies.
        AbilityFactory.AfterStatusDiscardFrom(
            AbilityType.Response,
            CardFinder(trait="DEFENDER"),
            "Tough",
            fogwells_gym,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
