from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        count = 3 if Worlds.IsExpert(effect) else 2
        cards = Worlds.DiscardEncounterCards(count, effect)
        if Filter.ByType(cards, Treachery):
            Faces.ExhaustAll([message.GetToPlayer().GetIdentity()], effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
