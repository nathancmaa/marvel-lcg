from . import *

# Ares's Axe


def GetAbilities() -> Sequence['Ability']:

    def discard_if_attack_dealt_no_damage(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        Faces.DiscardAll([effect.this], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Ares", card_type=Minion),
            otherwise_attach_to=Villain,
        ),
        AbilityFactory.AfterUnitAttackEnd(
            AbilityType.ForcedResponse,
            "AttachedEnemy",
            discard_if_attack_dealt_no_damage,
            conditions=[
                lambda effect, message:
                    not message.damaged_targets,
            ],
        ),
    ]
