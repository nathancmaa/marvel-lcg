from . import *

# * Moon Knight


def GetAbilities() -> Sequence['Ability']:

    def moon_knight(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        if not player:
            return
        discard = Worlds.GetEncounterDiscardPile(effect)
        for face in reversed(discard.Get()):
            if Treachery.IsType(face):
                Faces.ResolveAbility([face], player, AbilityType.WhenRevealed, effect)
                return

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            moon_knight,
        ),
    ]
