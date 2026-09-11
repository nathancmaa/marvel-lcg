from . import *

# Young Avengers


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.FirstCardPlayerRevealsGain(
            CardFinder(card_type=Minion),
            "AnyPlayer",
            each_phase_round="Round",
            gain_surge=1,
        ),
    ]
