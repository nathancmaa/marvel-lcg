from . import *


def GetAbilities() -> Sequence['Ability']:
    return FocusAbilities(3, total=True)
