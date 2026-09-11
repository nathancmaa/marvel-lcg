from . import *

# Knuckle Sandwich


def GetAbilities() -> Sequence['Ability']:

    def knuckle_sandwich(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.DealDamage(effect.targets, 3, effect)

        luke = FindLukeCage(effect)
        if not luke or ToughOn(luke) <= 0:
            return

        initiator = effect.GetInitiator()
        initiator.MayChooseOneAbility(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Discard a tough status card from Luke Cage to take"
                " Knuckle Sandwich back into your hand",
                lambda targets: (
                    luke.CastTo(CanStatus).DiscardTough(effect, rule=1),
                    Faces.ReturnToHand([this], initiator, effect),
                ),
            ),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            knuckle_sandwich,
        ).SetPlay().SetLabel("attack")
        .SetTarget(Enemy),
    ]
