from . import *

# Goblin

def GetAbilities() -> Sequence['Ability']:

    def goblin_defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        this = effect.this.CastTo(Minion)
        Unused(this)

        first_player = Worlds.GetFirstPlayer(effect)
        faces = Worlds.GetOnFieldSchemes(effect, finder=CardFinder(has_threat=True))
        face = first_player.AskChooseFace(faces, effect)
        if face:
            this.RemoveThreatFromSchemes([face], 2, effect)


    physical_card = CardFinder(has_printed_res="R")

    def prevent_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.PreventDamage("All", effect)

    def source_has_no_printed_physical_resource(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
        # Only a player card with a printed [physical] resource may damage
        # Goblin. Damage from an identity (Retaliate) or any other source
        # without printed resources is prevented too.
        from game.card.face.base import ClassCard
        source = message.by_effect.this
        return not ClassCard.IsType(source) or not physical_card.Check(source)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            "This",
            prevent_damage,
            conditions=[source_has_no_printed_physical_resource],
        ),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            goblin_defeated
        ),
    ]

