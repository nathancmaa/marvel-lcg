from . import *
from cards.pack.aoa.campaign import GetMissionScheme

# Worldwide Crisis

def GetAbilities() -> Sequence['Ability']:

    def worldwide_crisis_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        Unused(this)

        player = message.GetToPlayer()
        identity = player.GetIdentity()
        mission = GetMissionScheme(effect)

        def action(targets: Sequence[CardFace]):
            identity.TakeDamage(this, 1, effect)
            ThisCardGainSurge(effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Place 3 threat on the [[Mission]] side scheme",
                lambda targets:
                    this.PlaceThreatOnSchemes(targets, 3, effect)
            ).SetTarget([mission] if mission else []),
            AbilityFactory.ForChoiceAbility(
                "Take 1 damage and this card gains surge",
                action,
            ).SetTarget([identity])
        )

    def worldwide_crisis_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Treachery)
        Unused(this)

        mission = GetMissionScheme(effect)
        schemes = [mission] if mission else []
        this.PlaceThreatOnSchemes(schemes, 1, effect)

        message.GiveActivatingEnemyAdditionalBoostCard(1, effect)


    return [
        AbilityFactory.WhenThisRevealed(
            None,
            worldwide_crisis_revealed
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            worldwide_crisis_boost
        ),
    ]

