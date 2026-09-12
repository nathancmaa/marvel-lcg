from . import *

# Deadly Duo


def GetAbilities() -> Sequence['Ability']:

    def deadly_duo(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Players.ForEachPlayer(
            effect,
            lambda player: player.DiscardDeckTopCards(8, effect),
        )

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            deadly_duo,
        ),
    ]
