from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Faces.GiveStatus([message.GetToPlayer().GetIdentity()], "Stunned", effect)

    def after_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        if Faces.GiveStatus([message.attacked], "Stunned", effect):
            Faces.DiscardAll([effect.this], effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        identity = message.GetToPlayer().GetIdentity()
        if identity.IsStunned():
            identity.TakeDamage(effect.this, 1, effect)
        else:
            Faces.GiveStatus([identity], "Stunned", effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(KINGPIN),
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            KINGPIN,
            Hero,
            after_attack,
            target_took_damage=True,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
