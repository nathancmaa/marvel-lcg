from . import *

# * Spider-Woman: Mattie Franklin


def GetAbilities() -> Sequence['Ability']:

    def spider_woman(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> None:
        this = effect.this.CastTo(Ally)
        Faces.PlaceCountersOn([this], 1, LIMB_COUNTER, effect, maximum=8)

        limbs = this.GetCounters(LIMB_COUNTER)
        if limbs <= 0:
            return

        # The cash-out is the second half of the same Response, so it is offered
        # here rather than as an action of its own: she can only be spent on the
        # back of a thwart.
        player = this.GetOwnerPlayer()
        player.MayChooseOneAbility(
            effect,
            AbilityFactory.ForChoiceAbility(
                f"Discard Spider-Woman to deal {limbs} damage to an enemy",
                lambda targets: this.DealDamage(targets, limbs, effect),
            ).SetTarget(Enemy)
            .SetCostFunc(CostFunc.Discard("This")),
        )

    return [
        AbilityFactory.AfterUnitThwartEnd(
            AbilityType.Response,
            "YouControlCharacter",
            spider_woman,
        ),
    ]
