from . import *

# Jester's Yo-Yo


def GetAbilities() -> Sequence['Ability']:

    def yo_yo(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        discarded = player.DiscardControlCards(
            effect,
            highest_cost=True,
            control=True,
        ) if player else None
        # Nothing under their control to take: the yo-yo comes back round.
        if not discarded:
            this.GainSurge(1, effect)

    def yo_yo_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if player:
            player.DiscardControlCards(effect, upgrade=True)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            yo_yo,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            yo_yo_boost,
        ),
    ]
