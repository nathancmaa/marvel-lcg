from . import *

# Superspeed


def GetAbilities() -> Sequence['Ability']:

    def superspeed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        if not player:
            return
        discarded = player.DiscardRandomHandCards(1, effect)
        cost = FacesCounter.GetPrintedCost(discarded or [])
        if cost > 0:
            player.GetIdentity().TakeIndirectDamage(this, cost, effect)

    def superspeed_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if player:
            # A chosen card here, not a random one: the boost half says only
            # "discard 1 card from your hand".
            player.DiscardHandCards((1, 1), effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            superspeed,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            superspeed_boost,
        ),
    ]
