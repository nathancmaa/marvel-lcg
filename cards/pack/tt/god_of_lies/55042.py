from . import *

# * Fenris Wolf

def GetAbilities() -> Sequence['Ability']:

    def fenris_wolf(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        Unused(message)
        PlaceSynergyCounters("Mounting Resistance", 1)(effect)


    return [
        WhenDefeatedPlaceShatterCountersOnTheAvatarOfLokivillain(3, fenris_wolf)
    ]
