from . import *

# * Atlas


def GetAbilities() -> Sequence['Ability']:
    return ThunderboltAbilities(
        lambda player, effect:
            Faces.GiveStatus([player.GetIdentity()], "Stunned", effect),
    )
