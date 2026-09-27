from . import *


def GetAbilities() -> Sequence['Ability']:
    def add_threat_to_worlds(effect: 'Effect') -> None:
        worlds = Worlds.FindCardOnField(
            effect,
            name="Worlds Collide",
            card_type=MainScheme,
        )
        if worlds:
            worlds.PlaceThreatOnSchemes([worlds], 1, effect)

    def completed(effect: 'Effect', message: 'Message.WhenMainSchemeStageWouldBeCompleted') -> None:
        scheme = effect.this.CastTo(MainScheme)
        message.SetBeInstead(effect)
        scheme.RemoveThreatFromSchemes([scheme], "All", effect, ignore_crisis=True)
        add_threat_to_worlds(effect)

    def identity_defeated(effect: 'Effect', message: 'Message.WhenUnitWouldBeDefeated') -> None:
        identity = message.trigger.CastTo(Identity)
        message.SetBeInstead(effect)
        identity.SetHealth(1, effect)
        identity.ChangeToForm(AlterEgo, effect)
        add_threat_to_worlds(effect)

    return [
        AbilityFactory.WhenMainSchemeStageWouldBeCompleted(
            AbilityType.ForcedInterrupt,
            "This",
            completed,
        ),
        AbilityFactory.WhenUnitWouldBeDefeated(
            AbilityType.ForcedInterrupt,
            Identity,
            identity_defeated,
        ),
    ]
