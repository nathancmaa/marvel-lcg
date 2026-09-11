from . import *

# Power Man and Iron Fist


def GetAbilities() -> Sequence['Ability']:

    def power_man_and_iron_fist(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.DealDamage(effect.targets, 2, effect)
        Faces.GiveStatus(effect.targets2, "Tough", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            power_man_and_iron_fist,
        ).SetPlay().SetLabel("attack")
        .SetTarget(Enemy)
        # Any character, not only yours: Team-Up cards are written for a table.
        .SetTarget2("Character", canbe_tough=True),
    ]
