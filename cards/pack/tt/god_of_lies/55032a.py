from . import *


def GetAbilities() -> Sequence['Ability']:
    def wretch(effect: 'Effect', message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme') -> None:
        card = Worlds.DiscardEncounterTopCard(effect)
        if Treachery.IsType(card):
            effect.this.CastTo(Villain).GainForThisActive(
                effect,
                message,
                attack=1,
                scheme=1,
            )

    return [
        AbilityFactory.WhenUnitMakeAttack(
            AbilityType.ForcedInterrupt,
            "This",
            wretch,
        ),
        AbilityFactory.WhenUnitWouldScheme(
            AbilityType.ForcedInterrupt,
            "This",
            wretch,
        ),
        AvatarWouldBeDefeated(),
    ]
