from . import *


def IsTeamUpCard(face: 'CardFace') -> bool:
    # There is no finder flag for the keyword, so this reads the parsed TeamUp
    # attribute: a card without the keyword keeps the empty pair it starts with.
    return HasTeamUp.IsType(face) and any(face.team_up)


def GetAbilities() -> Sequence['Ability']:

    def defend_our_city(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        finder = CardFinder(check_face_fn=IsTeamUpCard)

        def search_for_player(player: 'Player') -> None:
            face = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                include_discard_pile=True,
                finder=finder,
                may=True,
            )
            if face:
                Faces.MoveAllTo([face], player.hand_cards, effect)

        Players.ForEachPlayer(effect, search_for_player)

        # Every Team-Up card, not only the ones just found, and for everybody:
        # the discount is its own sentence on the card.
        Worlds.UpdateNextCardPlayCost(
            "Any",
            -1,
            effect,
            finder=finder,
            in_this="Phase",
        )

    return [
        # Prerequisite ([[DEFENDER]]) -- checked when the scheme is played
        # rather than when it is defeated.
        AbilityFactory.CanPlayThisSchemeCard(
            conditions=[
                lambda effect, message:
                    effect.GetInitiator().GetIdentity().HasTrait("DEFENDER"),
            ],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defend_our_city,
        ),
    ]
