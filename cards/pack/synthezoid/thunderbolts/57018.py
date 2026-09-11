from . import *

# * Songbird


def GetAbilities() -> Sequence['Ability']:
    return ThunderboltAbilities(
        lambda player, effect:
            Faces.GiveStatus([player.GetIdentity()], "Confused", effect),
    )
