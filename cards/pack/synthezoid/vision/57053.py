from . import *

# Phase Disruption


def GetAbilities() -> Sequence['Ability']:

    def phase_disruption(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        if not player:
            return

        intangible = MassFormIs(effect, INTANGIBLE)

        def take_it(targets: Sequence['CardFace']) -> None:
            if intangible:
                Faces.DiscardAll(targets, effect)
            else:
                Faces.ExhaustAll(targets, effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Discard an upgrade you control" if intangible
                else "Exhaust an upgrade you control",
                take_it,
            ).SetTarget(Upgrade, from_where=["YouControlCards"],
                        canbe_discard=intangible or None,
                        canbe_exhaust=None if intangible else True),
        )

        if MassFormIs(effect, DENSE):
            FlipMassForm(effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            phase_disruption,
        ),
    ]
