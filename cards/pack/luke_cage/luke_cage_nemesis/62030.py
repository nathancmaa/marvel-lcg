from . import *

# Venomous Whispers


def GetAbilities() -> Sequence['Ability']:

    def when_defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        if not player:
            return
        face = Worlds.DiscardEncounterCardsUntil(
            effect,
            card_type=Minion,
            trait="SERPENT SOCIETY",
        )
        if face:
            face.Reveal(player, effect)

    def whispers_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        if player:
            Faces.GiveStatus([player.GetIdentity()], "Confused", effect)

    return [
        # While this is out, the Serpent Society has to be thwarted off the
        # table rather than punched off it.
        *AbilityFactory.UnitCannotAttackTarget(
            None,
            cannot_attack=CardFinder(trait="SERPENT SOCIETY", card_type=Minion),
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            when_defeated,
            has_defeating_player=True,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            whispers_boost,
        ),
    ]
