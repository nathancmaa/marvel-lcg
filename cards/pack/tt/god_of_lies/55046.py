from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Unused(message)
        PlaceShatterCountersOnTheAvatarOfLokivillain(3, effect)
        environments = CardFinder(
            trait="SYNERGY",
            card_type=Environment,
        ).Checks(Worlds.GetOnFieldCards(effect.this.card.GetGameArea()))
        if environments:
            environment = Filter.One(environments, effect)
            Faces.PlaceCountersOn(
                [environment],
                1,
                'synergy',
                effect,
                maximum=Worlds.GetPlayerNumIcon(effect),
            )

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
    ]
