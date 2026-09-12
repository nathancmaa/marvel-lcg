from . import *

# Strategic Overwatch


def GetAbilities() -> Sequence['Ability']:

    def strategic_overwatch(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        targets: List['CardFace'] = list(Worlds.GetOnFieldMinions(effect))
        leader = EnemyLeader(effect)
        if leader:
            targets.append(leader)
        Faces.GiveStatus(targets, "Tough", effect)

    def strategic_overwatch_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        Faces.GiveStatus([message.activating_enemy], "Tough", effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            strategic_overwatch,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            strategic_overwatch_boost,
        ),
    ]
