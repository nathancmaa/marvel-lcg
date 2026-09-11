from . import *

# * Wiccan


def GetAbilities() -> Sequence['Ability']:
    return ScarletTwinAbilities(
        lambda player, effect:
            effect.this.PlaceThreatOnSchemes("MainScheme", 2, effect),
    )
