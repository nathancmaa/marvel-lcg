from . import *

# Protect Secret Identities


def GetAbilities() -> Sequence['Ability']:

    def mill_the_table(effect: 'Effect', message: 'Message.AfterResolveVillainPhaseStep') -> None:
        Players.ForEachPlayer(
            effect,
            lambda player: player.DiscardDeckTopCards(3, effect),
        )

    return [
        AbilityFactory.ThisGainKeyword(
            check_fn=lambda effect, ui:
                Worlds.GetYourTeamSize(effect) > 1,
            hinder="2*",
        ),
        AbilityFactory.AfterResolveVillainPhaseStep(
            AbilityType.ForcedResponse,
            1,
            mill_the_table,
        ),
    ]
