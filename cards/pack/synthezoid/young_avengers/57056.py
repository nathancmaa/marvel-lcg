from . import *

# * Hawkeye


def GetAbilities() -> Sequence['Ability']:

    def hawkeye(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        if player:
            player.DiscardControlCards(effect, upgrade=True)

    return [
        AbilityFactory.UnitAttackGainKeyword(
            "This",
            None,
            piercing=True,
            ranged=True,
        ),
        AbilityFactory.WhenThisRevealed(
            None,
            hawkeye,
        ),
    ]
