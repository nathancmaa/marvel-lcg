from . import *

# Enforce the Law


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.ThisGainKeyword(
            check_fn=lambda effect, ui:
                Worlds.GetYourTeamSize(effect) > 1,
            hinder="2*",
        ),
        # "The enemy leader gains steady": read cooperatively, that is the
        # leader on the table, so stun stops landing on it once this stage is up.
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            Leader,
            steady=1,
        ),
    ]
