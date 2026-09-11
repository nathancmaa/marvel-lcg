from . import *

# * Burstein Process


def GetAbilities() -> Sequence['Ability']:

    def burstein_process(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        luke = FindLukeCage(effect)
        if not luke:
            return
        # Two if he is starting from nothing, which is what makes this worth an
        # action on a turn he has already been hit.
        count = 2 if ToughOn(luke) == 0 else 1
        for _ in range(count):
            Faces.GiveStatus([luke], "Tough", effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            burstein_process,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
