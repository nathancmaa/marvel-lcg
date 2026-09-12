from . import *

# S.H.I.E.L.D. Operator


def GetAbilities() -> Sequence['Ability']:

    def shield_operator(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        this.PlaceThreatOnSchemes("MainScheme", 2, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            shield_operator,
        ),
    ]
