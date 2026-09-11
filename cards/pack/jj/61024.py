from . import *

# Entrapment


def GetAbilities() -> Sequence['Ability']:

    def entrapment(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        this = effect.this.CastTo(Upgrade)
        effect.targets[0].CastTo(Identity).ChangeToForm(Hero, effect)
        # The villain that just schemed, and the threat it actually placed --
        # boost icons and any modifier included.
        this.DealDamage([message.trigger], message.placed_threat, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(),
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.AlterEgoResponse,
            Villain,
            entrapment,
        ).SetLabel("attack")
        .SetCostFunc(CostFunc.Discard("This"))
        .SetTarget("YourIdentity"),
    ]
