from . import *

# Mass Increase


def GetAbilities() -> Sequence['Ability']:

    def solid_wall(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        message.PreventDamage("All", effect)
        if message.would_atk_message:
            Faces.GiveStatus([message.would_atk_message.trigger], "Stunned", effect)
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Vision", card_type=Leader),
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            solid_wall,
            is_from_attack=True,
            conditions=[
                # Only while he is solid. Intangible Vision is not a wall to
                # bounce off, and the card waits rather than firing.
                lambda effect, message: MassFormIs(effect, DENSE),
            ],
        ),
    ]
