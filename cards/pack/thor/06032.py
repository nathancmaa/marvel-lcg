from . import *

# Teamwork

def GetAbilities() -> Sequence['Ability']:

    def teamwork(effect: 'Effect', message: 'Message.WhenUnitUseBasicPower') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        allies = effect.cost_func.Get(CostFunc.Exhaust).return_exhausted_cards
        allies = Filter.ByType(allies, Ally)

        # The would-attack/would-thwart message knows which power is really
        # used: thwarting an assault scheme uses ATK, so the allies' ATK is added.
        for ally in allies:
            message.would_message.AddMatchingPowerToThisPerformance(ally, effect)


    return [
        AbilityFactory.WhenUnitUseBasicPower(
            AbilityType.HeroInterrupt,
            "You",
            teamwork,
            powers=["THW", "ATK"]
        ).SetPlay().SetLabel()
        .SetCostFunc(CostFunc.Exhaust("YourAlly")),
    ]

