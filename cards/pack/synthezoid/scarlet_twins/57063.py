from . import *

# Spellcasting


def GetAbilities() -> Sequence['Ability']:

    def spellcasting(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> None:
        this = effect.this.CastTo(Obligation)
        message.CancelEffects(effect, discard_it=True)
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.WhenPlayerWouldPlayCard(
            AbilityType.ForcedInterrupt,
            "You",
            None,
            spellcasting,
            conditions=[
                lambda effect, message: not message.be_cancel,
            ],
        ),
    ]
