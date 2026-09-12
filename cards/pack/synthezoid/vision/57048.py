from .gear import *

# * Vision's Cape


def GetAbilities() -> Sequence['Ability']:
    return VisionGearAbilities(Cost("YB"), retaliate=1)
