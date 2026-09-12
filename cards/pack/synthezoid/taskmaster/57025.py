from . import *

# Mimicked Move


def GetAbilities() -> Sequence['Ability']:

    def mimicked_move(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        taskmaster = Worlds.FindCardOnField(effect, name="Taskmaster", card_type=Minion)
        # He can only copy a move against a leader, and cooperatively the
        # players have none -- so the second sentence is what resolves.
        if taskmaster and Worlds.GetYourTeamLeader(effect):
            assert False

        leader = EnemyLeader(effect)
        if leader:
            Faces.GiveStatus([leader], "Tough", effect)
            Faces.GiveFacedownBoostCards([leader], 1, effect)

    def mimicked_move_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        message.GiveBoostCardForThisActivation(Enemy, 1, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            mimicked_move,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            mimicked_move_boost,
        ),
    ]
