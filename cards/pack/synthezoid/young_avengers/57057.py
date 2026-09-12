from . import *

# * Stature


def GetAbilities() -> Sequence['Ability']:

    def stature(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        if player:
            player.DiscardControlCards(effect, support=True)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            stature,
        ),
    ]
