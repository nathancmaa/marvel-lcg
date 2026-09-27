from . import *

# Dynamic Duo


def GetAbilities() -> Sequence['Ability']:

    def dynamic_duo(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()

        # Both searches leave the deck alone (not_move) and the deck is
        # shuffled once, after both cards are in hand, whether they came from
        # the deck or the discard pile. A search that finds nothing already
        # shuffles the deck it looked through, so that is the one shuffle.
        team_up = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            include_discard_pile=True,
            not_move=True,
            finder=CardFinder(check_face_fn=IsTeamUpCard),
        )
        if team_up:
            Faces.AddToHand([team_up], player, effect)

            # The ally the Team-Up card names -- either of the two, since both
            # are "named by that card's Team-Up keyword" and only one of them
            # is likely to be an ally at all.
            names = [name for names in team_up.CastTo(HasTeamUp).team_up for name in names]
            ally = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                include_discard_pile=True,
                not_move=True,
                finder=CardFinder(card_type=Ally, check_face_fn=lambda face:
                                  any(face.IsName(name) for name in names)),
            )
            if ally:
                Faces.AddToHand([ally], player, effect)
                player.player_deck.Shuffle(effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            dynamic_duo,
        ).SetPlay().SetLabel(),
    ]
