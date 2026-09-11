from . import *

# * Squirrel Girl: Doreen Green


def GetAbilities() -> Sequence['Ability']:

    def gather_squirrels(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Ally)
        initiator = effect.GetInitiator()
        Faces.PlaceCountersOn(
            [this], initiator.hand_cards.GetSize(), SQUIRREL_COUNTER, effect,
            maximum=4,
        )

    def spend_a_squirrel(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Ally)
        this.RemoveThreatFromSchemes(effect.targets, 1, effect)

    return [
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.Response,
            "You",
            "This",
            gather_squirrels,
        ),
        # No exhaust cost: the printed action spends a counter and nothing else,
        # so she can still attack or thwart in the same turn.
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            spend_a_squirrel,
        ).SetCostFunc(CostFunc.Counter("This", 1, SQUIRREL_COUNTER))
        .SetTarget(Scheme2),
    ]
