from . import *

# Crescent Dart


def GetAbilities() -> Sequence['Ability']:

    def thrown(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        this = effect.this.CastTo(Attachment)
        message.GainPiercing(effect)
        message.GainRanged(effect)
        RunAt.AfterResolveMessage(effect, message, lambda: Faces.DiscardAll([this], effect))

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Moon Knight") | CardFinder(card_type=Leader),
        ),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            None,
            thrown,
        ),
    ]
