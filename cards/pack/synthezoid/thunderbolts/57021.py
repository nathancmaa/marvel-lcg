from . import *

# The Thunderbolts


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            while_face_is_in_play=CardFinder(trait="THUNDERBOLT", card_type=Minion),
        ),
    ]
