from . import *

# Toughen Up


def GetAbilities() -> Sequence['Ability']:

    def toughen_up(effect: 'Effect', message: 'Message.AfterUnitRecovery') -> None:
        identity = effect.GetInitiator().GetIdentity()
        Faces.GiveStatus([identity], "Tough", effect)

    def back_to_full(effect: 'Effect', message: 'Message.AfterUnitRecovery') -> bool:
        # "equal to or greater than your base hit points": a recover that only
        # took the edge off does not qualify.
        identity = effect.GetInitiator().GetIdentity()
        return CanHealth.IsType(identity) and identity.health >= identity.base_health

    return [
        AbilityFactory.CanPlayThisUpgradeCard(),
        AbilityFactory.AfterUnitRecovery(
            AbilityType.Response,
            "You",
            toughen_up,
            conditions=[back_to_full],
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
