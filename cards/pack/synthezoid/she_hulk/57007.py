from . import *

# Superhuman Strength


def GetAbilities() -> Sequence['Ability']:

    def swing_harder(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        this = effect.this.CastTo(Attachment)
        message.GainOverKill(effect)
        # After this attack, not immediately: the overkill has to land first.
        RunAt.AfterResolveMessage(effect, message, lambda: Faces.DiscardAll([this], effect))

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="She-Hulk", card_type=Leader)
        ),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            None,
            swing_harder,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            RevealThisCard,
        ),
    ]
