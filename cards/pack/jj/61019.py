from . import *

# Strategy Session


def GetAbilities() -> Sequence['Ability']:

    def find_a_side_scheme(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.targets[0].GetControlByPlayer()
        # The deck only -- this one does not reach the discard pile.
        face = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            card_type=PlayerSideScheme,
        )
        if face:
            Faces.AddToHand([face], player, effect)

    def thwart_a_side_scheme(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.RemoveThreatFromSchemes(effect.targets, 3, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            find_a_side_scheme,
        ).SetPlay().SetLabel()
        .SetTarget("Players"),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            thwart_a_side_scheme,
        ).SetPlay().SetLabel("thwart")
        .SetTarget(card_type=PlayerSideScheme),
    ]
