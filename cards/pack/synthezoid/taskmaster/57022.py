from . import *

# * Taskmaster


def GetAbilities() -> Sequence['Ability']:

    def taskmaster(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetToPlayer()
        if player:
            this.DoActivate(player, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            taskmaster,
        ),
    ]
