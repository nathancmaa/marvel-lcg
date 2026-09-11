from . import *

# Dynamic Duo


def GetAbilities() -> Sequence['Ability']:

    def dynamic_duo(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()

        team_up = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            include_discard_pile=True,
            finder=CardFinder(check_face_fn=IsTeamUpCard),
        )
        if not team_up:
            return
        Faces.AddToHand([team_up], player, effect)

        # The ally the Team-Up card names -- either of the two, since both are
        # "named by that card's Team-Up keyword" and only one of them is likely
        # to be an ally at all.
        names = [name for names in team_up.CastTo(HasTeamUp).team_up for name in names]
        ally = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            include_discard_pile=True,
            finder=CardFinder(card_type=Ally, check_face_fn=lambda face:
                              any(face.IsName(name) for name in names)),
        )
        if ally:
            Faces.AddToHand([ally], player, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            dynamic_duo,
        ).SetPlay().SetLabel(),
    ]
