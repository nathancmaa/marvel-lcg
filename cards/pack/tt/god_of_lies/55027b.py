from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        ResolveStageTwoFocus(effect, message.GetToPlayer())

    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        Unused(message)
        Worlds.SetGameOver(True, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.NonKeywordBold,
            "This",
            defeated,
        ),
    ]
