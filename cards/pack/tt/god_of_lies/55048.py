from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Unused(message)
        PlaceShatterCountersOnTheAvatarOfLokivillain(3, effect)
        PlaceSynergyCounters("Feigned Retreat", 1)(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
    ]
