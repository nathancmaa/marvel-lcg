from .gear import *

# * Solar Gem


def GetAbilities() -> Sequence['Ability']:
    return VisionGearAbilities(Cost("YR"), stalwart=1)
