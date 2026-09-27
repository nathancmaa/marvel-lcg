from . import *


def GetAbilities() -> Sequence['Ability']:
    def attacked(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        card = Worlds.DiscardEncounterTopCard(effect)
        if Treachery.IsType(card):
            Faces.GiveStatus([message.attacker], "Stunned", effect)

    return [
        AbilityFactory.AfterUnitAttackEnd(
            AbilityType.ForcedResponse,
            Friend,
            attacked,
            against_who="This",
        ),
        WhenDefeatedPlaceShatterAndSynergy(3, "Unified Front"),
    ]
