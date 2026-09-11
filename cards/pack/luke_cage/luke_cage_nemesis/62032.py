from . import *

# * Asp


def GetAbilities() -> Sequence['Ability']:

    def asp_schemes(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        player = message.GetAgainstPlayer()
        if player:
            Faces.GiveStatus([player.GetIdentity()], "Stunned", effect)

    def asp_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if player:
            Faces.GiveStatus([player.GetIdentity()], "Stunned", effect)

    return [
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "This",
            asp_schemes,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            asp_boost,
        ),
    ]
