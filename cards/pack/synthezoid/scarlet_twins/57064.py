from . import *

# Superpowered Siblings


def GetAbilities() -> Sequence['Ability']:

    def superpowered_siblings(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        if player:
            player.DiscardHandCards((1, 1), effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            superpowered_siblings,
            has_defeating_player=True,
        ),
    ]
