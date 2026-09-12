from . import *

# Cruisin' for a Bruisin'


def GetAbilities() -> Sequence['Ability']:

    def gain_overkill(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        message.GainOverKill(effect)
        message.IncreaseDamage(2, effect)

    def engage_him(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Upgrade)
        minion = this.attached_face
        if minion and Minion.IsType(minion):
            minion.EngagePlayer(effect.GetInitiator(), effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(Minion),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.NonKeyword,
            None,
            "AttachedMinion",
            gain_overkill,
        ),
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.Response,
            "You",
            "This",
            engage_him,
        ),
    ]
