from . import *

# Metal Bracer


def GetAbilities() -> Sequence['Ability']:

    def metal_bracer(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        # Refused outright on Luke Cage's own unpreventable damage, which is
        # handled inside the message rather than here.
        message.ReduceDamage(1, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(),
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            retaliate=1,
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            "YourHero",
            metal_bracer,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
