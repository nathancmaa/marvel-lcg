from . import *

# Taskmaster's Academy


def GetAbilities() -> Sequence['Ability']:

    def graduation(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        leader = EnemyLeader(effect)
        if leader:
            Faces.GiveStatus([leader], "Tough", effect)
            Faces.GiveFacedownBoostCards([leader], 1, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            graduation,
        ),
    ]
