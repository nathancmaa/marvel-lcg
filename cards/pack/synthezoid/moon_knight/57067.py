from . import *

# Fist of Khonshu


def GetAbilities() -> Sequence['Ability']:

    def fist_of_khonshu(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        if not player:
            return
        identity = player.GetIdentity()
        Faces.ExhaustAll([identity], effect)
        this.DealDamage([identity], 2, effect)

    def fist_of_khonshu_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if player:
            Faces.ExhaustAll([player.GetIdentity()], effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            fist_of_khonshu,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            fist_of_khonshu_boost,
        ),
    ]
