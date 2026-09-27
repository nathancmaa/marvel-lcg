from . import *


def GetAbilities() -> Sequence['Ability']:
    def knave(effect: 'Effect', message: 'Message.AfterCardRevealed') -> None:
        player = message.GetToPlayer()
        identity = player.GetIdentity()
        identity.TakeDamage(effect.this, 1, effect)
        allies = player.GetControlAllies()
        if allies:
            ally = Filter.One(allies, effect)
            ally.TakeDamage(effect.this, 1, effect)

    return [
        Ability(
            AbilityType.ForcedResponse,
            Message.AfterCardRevealed,
            [
                lambda effect, message: Treachery.IsType(message.trigger),
            ],
            knave,
        ),
        AvatarWouldBeDefeated(),
    ]
