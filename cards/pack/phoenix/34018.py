from . import *

# Mutant Peacekeepers

def GetAbilities() -> Sequence['Ability']:

    def mutant_peacekeepers(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()
        identity = initiator.GetHero()
        value = identity.thwart
        for face in effect.cost_func.Get(CostFunc.Exhaust, index=1).return_exhausted_cards:
            if HasThwart.IsType(face):
                value += face.thwart
        initiator.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "",
                lambda targets:
                    this.RemoveThreatFromSchemesTotal(targets, value, effect),
            ).SetLabel('thwart')
            .SetTarget(Scheme2, range=("Zero", value), repeat_rules="Threat"),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            mutant_peacekeepers
        ).SetPlay(only_if_your_identity_has_trait="X-MEN").SetLabel('thwart')
        .SetCostFunc(CostFunc.Exhaust("YourHero"))
        .SetCostFunc(CostFunc.Exhaust(card_type=Ally, trait="X-MEN", range=(0, "All")))
        .SetTarget2(Scheme2),
    ]

