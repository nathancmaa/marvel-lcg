from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        cards = Worlds.DiscardEncounterCards(3, effect)
        if Filter.ByType(cards, Treachery):
            message.GetToPlayer().GetIdentity().TakeIndirectDamage(
                effect.this,
                2,
                effect,
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        WhenDefeatedPlaceShatterAndSynergy(3, "Domineering Force"),
    ]
