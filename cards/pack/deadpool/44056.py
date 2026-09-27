from . import *

# * Rock, Paper, Scissors

def _is_beat(a: Resources, b: Resources) -> bool:
    if a.val == 0 or b.val == 0:
        return False

    return (
        (a.g > 0 and (b.r > 0 or b.b > 0 or b.y > 0)) or
        (a.r > 0 and b.y > 0) or
        (a.b > 0 and b.r > 0) or
        (a.y > 0 and b.b > 0)
    )


def GetAbilities() -> Sequence['Ability']:

    def rock_paper_scissors(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        initiator = effect.GetInitiator()

        hand_face = effect.targets[0]
        deck_top_face = effect.cost_func.Get(CostFunc.Discard).return_discarded_cards[0]

        res1 = FacesCounter.GetPrintedResources([hand_face])
        res2 = FacesCounter.GetPrintedResources([deck_top_face])
        if _is_beat(res1, res2):
            initiator.GainCard(deck_top_face, effect)


    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            rock_paper_scissors
        ).SetTarget(from_where=["YourHandCards"])
        .SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Discard("YourPlayerDeckTop")),
    ]
