from . import *

# "Stand with Me!"


def GetAbilities() -> Sequence['Ability']:

    def stand_with_me(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        luke = FindLukeCage(effect)
        if luke:
            Faces.GiveStatus([luke], "Tough", effect)
        # Counted after the card is given, and capped at 5 by the card itself.
        this.RemoveThreatFromSchemes(
            effect.targets, min(ToughOn(luke), 5), effect,
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            stand_with_me,
        ).SetPlay().SetLabel("thwart")
        .SetTarget(Scheme2),
    ]
