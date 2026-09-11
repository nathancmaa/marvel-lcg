from . import *

# * Cottonmouth


def GetAbilities() -> Sequence['Ability']:

    def three_bites(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        this = effect.this.CastTo(Minion)
        target = message.attacked
        if not target:
            return
        # The same character, twice more. Each is a fresh attack, so boost
        # cards and anything watching for an attack fire again.
        for _ in range(2):
            if not this.IsInPlay() or target.IsDefeated():
                return
            this.DoAttackUnit(target, effect)

    def cottonmouth_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this
        player = FindLukeCagePlayer(effect) or message.GetToPlayer()
        if player:
            player.DealEncounterCard(this, effect)

    return [
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            "This",
            None,
            three_bites,
        ).LimitOncePerPhase(),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            cottonmouth_boost,
        ),
    ]
