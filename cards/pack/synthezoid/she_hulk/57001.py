from .leader import *

# * She-Hulk


def GetAbilities() -> Sequence['Ability']:
    return SheHulkLeaderAbilities(stage_two=False)
