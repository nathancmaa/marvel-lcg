from . import *

# Homeland Security


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.FirstCardPlayerRevealsGain(
            CardFinder(card_type=Minion),
            "AnyPlayer",
            each_phase_round="Round",
            gain_surge=1,
        ),
    ]
