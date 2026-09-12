from . import *

# * Jester


def GetAbilities() -> Sequence['Ability']:

    def jester(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetToPlayer()
        if not player:
            return
        discarded = player.DiscardDeckTopCards(3, effect)
        # Per distinct type, not per card: three events off the top is one.
        types = DifferentCardTypes(discarded)
        if types > 0:
            player.GetIdentity().TakeIndirectDamage(this, types, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            jester,
        ),
    ]
