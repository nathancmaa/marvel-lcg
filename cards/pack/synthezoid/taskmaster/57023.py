from . import *

# * Taskmaster's Sword


def GetAbilities() -> Sequence['Ability']:
    return [
        # Taskmaster if he is here, the leader otherwise: the finders are tried
        # in order, so the more specific one comes first.
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Taskmaster") | CardFinder(card_type=Leader),
        ),
        AbilityFactory.UnitAttackGainKeyword(
            "AttachedCharacter",
            None,
            piercing=True,
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCostFunc(CostFunc.Spend(Cost("BR"))),
    ]
