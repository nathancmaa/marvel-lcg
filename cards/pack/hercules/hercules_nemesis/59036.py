from . import *

# * Ares


def GetAbilities() -> Sequence['Ability']:

    def ares_schemes(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        player = message.GetAgainstPlayer()
        assert player
        player.DealEncounterCards(1, effect)

    return [
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "This",
            ares_schemes,
        ),
    ]
