from . import *


def GetAbilities() -> Sequence['Ability']:
    def miscreant(effect: 'Effect', message: 'Message.AfterCardRevealed') -> None:
        main_scheme = Worlds.FindMainScheme(effect)
        if main_scheme:
            main_scheme.PlaceThreatOnSchemes([main_scheme], 1, effect)

        side_schemes = CardFinder(card_type=SchemeSide2).Checks(
            Worlds.GetOnFieldSchemes(effect),
        )
        if side_schemes:
            side_scheme = Filter.One(side_schemes, effect)
            side_scheme.PlaceThreatOnSchemes([side_scheme], 1, effect)

    return [
        Ability(
            AbilityType.ForcedResponse,
            Message.AfterCardRevealed,
            [
                lambda effect, message: Treachery.IsType(message.trigger),
            ],
            miscreant,
        ),
        AvatarWouldBeDefeated(),
    ]
