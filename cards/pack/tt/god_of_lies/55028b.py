from . import *


def GetAbilities() -> Sequence['Ability']:
    def prevent_unreferenced_threat(
        effect: 'Effect',
        message: 'Message.WhenSchemeWouldPlaceThreat',
    ) -> None:
        message.SetBeInstead(effect)

    return [
        AbilityFactory.PlayersCannotDamageUnit(
            "AnyPlayer",
            TRUE_LOKI,
            conditions=[
                lambda effect, message: message.by_effect.IsPlayerInitiator(),
            ],
        ),
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            from_where="This",
        ),
        AbilityFactory.WhenSchemeWouldPlaceThreat(
            AbilityType.NonKeyword,
            "This",
            prevent_unreferenced_threat,
            conditions=[
                lambda effect, message:
                    not message.by_effect.this.IsName("Mischief and Mayhem"),
            ],
        ),
    ]
