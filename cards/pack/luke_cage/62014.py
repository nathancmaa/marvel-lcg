from . import *

# * Valkyrie: Brunnhilde


def GetAbilities() -> Sequence['Ability']:

    def valkyrie(effect: 'Effect', message: 'Message.WhenUnitWouldBeDefeated') -> None:
        this = effect.this.CastTo(Ally)
        ally = message.trigger.CastTo(Unit2)

        message.SetBeInstead(effect)
        # "Heal that ally until they have 1 hit point remaining": the wording is
        # a floor, not a full heal -- whatever damage it takes to leave one.
        ally.SetHealth(1, effect)
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.WhenUnitWouldBeDefeated(
            AbilityType.Interrupt,
            Ally,
            valkyrie,
            conditions=[
                # Another ally, and one she shares a controller with.
                lambda effect, message:
                    message.trigger != effect.this
                    and message.trigger.GetControlBy() == effect.this.GetControlBy(),
            ],
        ),
    ]
