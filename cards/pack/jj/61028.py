from . import *


def GetAbilities() -> Sequence['Ability']:

    def second_chance(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        def action(player: 'Player') -> None:
            # Identity-specific by card class, not set name: Wasp's Pym
            # Particles and similar cards carry another set's name.
            cards = [
                face for face in player.discard_pile.GetAll()
                if ClassCard.IsType(face) and face.IsClass("IdentitySpecific")
            ]
            if cards:
                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Shuffle all identity-specific cards from your discard pile into your deck",
                        lambda targets: Faces.ShuffleAllTo(cards, player.player_deck, effect),
                    ),
                )

        Players.ForEachPlayer(effect, action)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            second_chance,
        ),
    ]
