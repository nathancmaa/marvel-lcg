from . import *

# Gamma Slam


def GetAbilities() -> Sequence['Ability']:

    def gamma_slam(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        discarded = player.DiscardControlCards(
            effect,
            highest_cost=True,
            finder=CardFinder(card_type=Ally | Support),
        ) if player else None

        cost = FacesCounter.GetPrintedCost([discarded]) if discarded else 0
        if cost > 0:
            this.PlaceThreatOnSchemes("MainScheme", cost, effect)
            return

        # Nothing worth taking, or a free card taken: either way no threat was
        # placed, and the card moves on.
        this.GainSurge(1, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            gamma_slam,
        ),
    ]
