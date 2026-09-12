from . import *

# Legal Practice


def GetAbilities() -> Sequence['Ability']:

    def argue_it_down(effect: 'Effect', message: 'Message.AfterUnitChangeForm') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        # Removed by the scheme itself rather than by a character, which is the
        # only way threat comes off this one.
        this.RemoveThreatFromSchemes([this], 3, effect)

    return [
        # Heroes and allies cannot shift it; the alter-ego response below can.
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            by_character=CardFinder(card_type=Hero | Ally),
        ),
        AbilityFactory.AfterUnitChangeForm(
            AbilityType.AlterEgoResponse,
            "You",
            argue_it_down,
        ).SetCostFunc(CostFunc.Exhaust("YourIdentity")),
    ]
