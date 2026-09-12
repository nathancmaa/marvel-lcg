from . import *

# Righteous Purpose


def OnTheirLastHitPoint(face: 'CardFace') -> bool:
    # "exactly 1 hit point remaining", so it switches off again the moment the
    # character is healed -- which is why the buff is re-evaluated on health.
    return CanHealth.IsType(face) and face.health == 1


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.CanPlayThisSupportCard(
            under_any_players_control=True
        ),
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            CardFinder(card_type=Unit2, check_face_fn=OnTheirLastHitPoint),
            control_by="You",
            attack=2,
            thwart=2,
            change_on_event=OnEvent.Health(None),
        ),
    ]
