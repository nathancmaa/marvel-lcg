from . import *

# Shakedown


def GetAbilities() -> Sequence['Ability']:

    def shakedown(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        this = effect.this.CastTo(Upgrade)
        minion = message.target
        if not HasScheme.IsType(minion):
            return
        if minion.base_scheme > 0:
            this.RemoveThreatFromSchemes(effect.targets, minion.base_scheme, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(
            "Players"
        ),
        # "exactly defeat" is an attack that left nothing over: a minion on 2
        # hit points taken down by a 3 damage attack does not qualify, and
        # neither does one finished off by anything that was not an attack.
        AbilityFactory.AfterUnitDefeatedUnit(
            AbilityType.Response,
            "You",
            Minion,
            shakedown,
            is_from_attack=True,
            has_excess_damage=False,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget(Scheme2),
    ]
