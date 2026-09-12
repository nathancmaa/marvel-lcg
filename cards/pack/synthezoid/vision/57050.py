from . import *

# Density Control


def GetAbilities() -> Sequence['Ability']:

    def pick_a_state(to: str):
        def run(effect: 'Effect', message: 'Message2') -> None:
            this = effect.this.CastTo(Attachment)
            # Only discards itself if the flip actually happened: he may already
            # be lying the right way round.
            if FlipMassForm(effect, to):
                Faces.DiscardAll([this], effect)
        return run

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Vision", card_type=Leader),
        ),
        # Schemes go through walls, attacks need something behind them.
        AbilityFactory.WhenUnitWouldScheme(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            pick_a_state(INTANGIBLE),
        ),
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            pick_a_state(DENSE),
        ),
    ]
