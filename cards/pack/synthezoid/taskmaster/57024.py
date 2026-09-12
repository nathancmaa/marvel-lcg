from . import *

# * Taskmaster's Shield


def GetAbilities() -> Sequence['Ability']:

    def turn_it_aside(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.ReduceDamage(1, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Taskmaster") | CardFinder(card_type=Leader),
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            turn_it_aside,
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCostFunc(CostFunc.Spend(Cost("BR"))),
    ]
