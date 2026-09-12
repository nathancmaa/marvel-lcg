from . import *

# * Speed


def GetAbilities() -> Sequence['Ability']:
    return ScarletTwinAbilities(
        lambda player, effect:
            effect.this.DealDamage([player.GetIdentity()], 2, effect),
    )
