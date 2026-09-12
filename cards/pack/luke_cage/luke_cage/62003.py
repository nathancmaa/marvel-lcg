from . import *

# Harlem's Hero


def GetAbilities() -> Sequence['Ability']:

    def harlems_hero(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        luke = FindLukeCage(effect)
        if luke:
            Faces.GiveStatus([luke], "Tough", effect)
        Faces.ReadyAll(effect.targets, effect)

    def how_many_to_ready(effect: 'Effect') -> int:
        # Counted after the tough card this event gives him, which is what the
        # card's own order means -- and he can always take another, so the one
        # about to be placed is never refused.
        luke = FindLukeCage(effect)
        return ToughOn(luke) + 1 if luke else 0

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            harlems_hero,
        ).SetPlay().SetLabel()
        .SetTarget("YouControlCharacter", canbe_ready=True,
                   range=(0, how_many_to_ready)),
    ]
