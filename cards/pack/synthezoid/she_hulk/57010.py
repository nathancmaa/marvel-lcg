from . import *

# Ground Stomp


def GetAbilities() -> Sequence['Ability']:

    def ground_stomp(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        if not player:
            return
        exhausted = Faces.ExhaustAll(player.GetControlCharacters(), effect)
        # Nothing left standing to knock over: the card keeps moving instead.
        if not exhausted:
            this.GainSurge(1, effect)

    def ground_stomp_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if not player:
            return
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust a character you control",
                lambda targets: Faces.ExhaustAll(targets, effect),
            ).SetTarget("YouControlUnit", canbe_exhaust=True),
        )

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            ground_stomp,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            ground_stomp_boost,
        ),
    ]
