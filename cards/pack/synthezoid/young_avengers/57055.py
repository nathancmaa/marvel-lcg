from . import *

# * Patriot


def GetAbilities() -> Sequence['Ability']:

    def patriot(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = EnemyLeader(effect)
        if leader:
            Faces.GiveStatus([leader], "Tough", effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            patriot,
        ),
    ]
