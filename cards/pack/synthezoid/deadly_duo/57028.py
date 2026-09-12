from . import *

# * Jack O'Lantern


def GetAbilities() -> Sequence['Ability']:

    def jack_o_lantern(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetToPlayer()
        if not player:
            return
        discarded = player.DiscardDeckTopCards(3, effect)
        types = DifferentCardTypes(discarded)
        if types > 0:
            this.PlaceThreatOnSchemes("MainScheme", types, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            jack_o_lantern,
        ),
    ]
