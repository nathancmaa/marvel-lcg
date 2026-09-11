from . import *

# * Misty Knight


def GetAbilities() -> Sequence['Ability']:

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.ThisGainKeyword(
            lambda effect, ui:
                effect.this.CastTo(Ally).tough > 0,
            attack=2,
            thwart=2,
            change_on_event=OnEvent.Status("This", 'Tough'),
        ),
    ]
