from . import *

# Internal Injury


def GetAbilities() -> Sequence['Ability']:

    def internal_injury(effect: 'Effect', message: 'Message.AfterPhaseEnd') -> None:
        this = effect.this
        identity = this.GetOwnerPlayer().GetIdentity()
        # Three, every phase, until he takes a turn off to recover. Ignoring
        # tough and unpreventable, so stacking up tough cards is no answer.
        identity.TakeDamage(
            this,
            DamageProperty(3, ignore_tough=True, unpreventable=True),
            effect,
        )

    return [
        AbilityFactory.AfterPhaseEnd(
            AbilityType.ForcedResponse,
            "Player",
            internal_injury,
        ),
        AbilityFactory.AfterUnitRecovery(
            AbilityType.AlterEgoResponse,
            "You",
            lambda effect, message: RemoveThisFromGame(effect, message),
        ),
    ]
