from .leader import *

# * Vision


def GetAbilities() -> Sequence['Ability']:
    return VisionLeaderAbilities(stage_two=True)
