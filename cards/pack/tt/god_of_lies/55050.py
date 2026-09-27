from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        avatar = FindAvatarOfLoki(effect)
        if avatar:
            Faces.RemoveCountersOn([avatar], 1, 'shatter', effect)
        damage = 3 if Worlds.IsExpert(effect) else 2
        message.GetToPlayer().GetIdentity().TakeDamage(effect.this, damage, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        player.GetIdentity().TakeIndirectDamage(
            effect.this,
            len(player.GetControlCharacters()),
            effect,
        )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
