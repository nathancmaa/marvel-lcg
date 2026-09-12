from . import *

# The Royal Guard


def GetAbilities() -> Sequence['Ability']:

    def the_royal_guard(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        if not player:
            return
        face = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            name="Blood Debt",
        )
        if face:
            player.DealEncounterCard(face, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            the_royal_guard,
            has_defeating_player=True,
        ),
    ]
