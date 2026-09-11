from . import *

# * Luke Cage


def GetAbilities() -> Sequence['Ability']:

    def unbreakable_skin(effect: 'Effect', message: 'Message.AfterStatusDiscardFrom') -> None:
        this = effect.this.CastTo(Hero)
        # Unpreventable and ignoring tough: the whole point is that shedding a
        # tough card costs him something Metal Bracer cannot argue with.
        this.TakeDamage(
            this,
            DamageProperty(1, ignore_tough=True, unpreventable=True),
            effect,
        )

    return [
        AbilityFactory.ThisCanHaveAdditionalTough("Any"),
        AbilityFactory.UnitAttackGainKeyword(
            None,
            "This",
            lost_piercing=True,
        ),
        AbilityFactory.AfterStatusDiscardFrom(
            AbilityType.ForcedResponse,
            "This",
            "Tough",
            unbreakable_skin,
        ).SetName("Unbreakable Skin"),
    ]
