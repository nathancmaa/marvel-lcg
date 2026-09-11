from . import *

# Khonshu's Avatar


def GetAbilities() -> Sequence['Ability']:

    def khonshus_avatar(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        if not player:
            return
        face = Worlds.DiscardEncounterCardsUntil(effect, card_type=Treachery)
        if face:
            Faces.ResolveAbility([face], player, AbilityType.WhenRevealed, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            khonshus_avatar,
            has_defeating_player=True,
        ),
    ]
