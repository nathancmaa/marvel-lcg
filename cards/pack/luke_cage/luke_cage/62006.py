from . import *

# "Sweet Christmas!"


def GetAbilities() -> Sequence['Ability']:

    def sweet_christmas(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.DealDamage(effect.targets, 5, effect)

    return [
        AbilityFactory.ReduceCostToPlayThis(
            lambda effect: ToughOn(FindLukeCage(effect)),
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            sweet_christmas,
        ).SetPlay().SetLabel("attack")
        .SetTarget("VillainAndYouEngagedMinion", range="All"),
    ]
