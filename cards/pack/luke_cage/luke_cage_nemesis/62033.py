from . import *

# * Sidewinder


def GetAbilities() -> Sequence['Ability']:

    def he_slips_away(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        this = effect.this.CastTo(Minion)
        discarded = Worlds.DiscardEncounterTopCard(effect)
        if not discarded:
            return
        # A "Boost" ability, not a boost icon -- nearly every encounter card
        # has the icons. This is the same test the boost star is drawn from.
        if not discarded.effect.Find(type=AbilityType.Boost):
            return
        attacker = message.trigger.GetControlByPlayer()
        if attacker:
            attacker.DealEncounterCard(this, effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            None,
            "This",
            he_slips_away,
        ),
    ]
