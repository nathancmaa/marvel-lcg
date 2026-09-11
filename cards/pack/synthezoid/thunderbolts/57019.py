from . import *

# * Penance


def GetAbilities() -> Sequence['Ability']:
    # Two when he is revealed, one when he is only a boost card.
    return ThunderboltAbilities(
        lambda player, effect:
            Utility.DealDamageToCharacterYouControl(player, 2, effect),
        lambda player, effect:
            Utility.DealDamageToCharacterYouControl(player, 1, effect),
    )
