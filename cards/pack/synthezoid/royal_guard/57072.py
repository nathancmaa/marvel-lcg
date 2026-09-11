from . import *

# Blood Debt


def GetAbilities() -> Sequence['Ability']:
    return [
        # The trait is what the Royal Guard's two minions look for; until it is
        # discarded they come straight at whoever is carrying it.
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            trait="HUNTED",
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetCostFunc(CostFunc.DiscardDeckTopCards("YourDeck", 8)),
    ]
