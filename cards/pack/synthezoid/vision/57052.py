from . import *

# Superdense Strike


def GetAbilities() -> Sequence['Ability']:

    def superdense_strike(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        if not player:
            return

        def hit_them(targets: Sequence['CardFace']) -> None:
            Faces.ExhaustAll(targets, effect)
            if MassFormIs(effect, DENSE):
                this.DealDamage(targets, 2, effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust a character you control",
                hit_them,
            ).SetTarget("YouControlUnit", canbe_exhaust=True),
        )

        # Both halves can apply: he is only ever lying one way, so at most one
        # of these fires on any given reveal.
        if MassFormIs(effect, INTANGIBLE):
            FlipMassForm(effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            superdense_strike,
        ),
    ]
