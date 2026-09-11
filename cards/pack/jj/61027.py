from . import *

# Unbreakable Bond


def GetAbilities() -> Sequence['Ability']:

    def unbreakable_bond(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.RemoveThreatFromSchemes(effect.targets, 3, effect)
        # One damage healed per selection, up to three, and the same character
        # may be chosen more than once -- which is what "a total of 3" means.
        this.HealthUnits(effect.targets2, 1, effect)

    def is_one_of_the_pair(effect: 'Effect', face: 'CardFace') -> bool:
        return face.IsName("Jessica Jones") or face.IsName("Luke Cage")

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            unbreakable_bond,
        ).SetPlay().SetLabel("thwart")
        .SetTarget(Scheme2)
        .SetTarget2("YouControlUnit", check_fn=is_one_of_the_pair,
                    repeat_rules="Sustained", range=(1, 3), canbe_heal=True),
    ]
