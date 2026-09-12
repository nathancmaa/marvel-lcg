from . import *

# Size Advantage


def GetAbilities() -> Sequence['Ability']:

    def size_advantage(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        identity = effect.GetInitiator().GetIdentity()

        def doubled_against(enemy: 'CardFace') -> bool:
            if identity.HasTrait("GIANT"):
                return True
            return CanHealth.IsType(enemy) and identity.health > enemy.health

        for enemy in effect.targets:
            this.DealDamage([enemy], 6 if doubled_against(enemy) else 3, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            size_advantage,
        ).SetPlay().SetLabel("attack")
        .SetTarget(Enemy),
    ]
