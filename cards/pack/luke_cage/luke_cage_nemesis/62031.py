from . import *

# Augmented Jaws


def GetAbilities() -> Sequence['Ability']:

    def strip_their_guard(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        target = message.attacked
        if target and CanStatus.IsType(target):
            target.DiscardAllTough(effect)

    return [
        # Cottonmouth if he is here, the villain otherwise -- the finders are
        # tried in order, so the more specific one comes first.
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Cottonmouth") | CardFinder(card_type=Villain),
        ),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            "AttachedEnemy",
            None,
            strip_their_guard,
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCostFunc(CostFunc.Spend(Cost("BB"))),
    ]
