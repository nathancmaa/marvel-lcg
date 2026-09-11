from . import *

# Intangible


def GetAbilities() -> Sequence['Ability']:

    def phase_through_it(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.ReduceDamage(1, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Vision", card_type=Leader),
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            phase_through_it,
        ),
    ]
