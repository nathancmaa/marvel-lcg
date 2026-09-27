from . import *

# Olympic Feud


def GetAbilities() -> Sequence['Ability']:

    def olympic_feud_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        olympus_cards = Worlds.FindCardSizeOnField(effect, trait="OLYMPUS")
        this.PlaceThreatOnSchemes([this], olympus_cards, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            olympic_feud_revealed,
        ),
    ]
