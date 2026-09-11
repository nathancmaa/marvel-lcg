from . import *

# * Iron Fist: Danny Rand


def GetAbilities() -> Sequence['Ability']:

    def iron_fist(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Ally)
        # His ATK as it stands, not as it is printed: Black Belt and Righteous
        # Purpose both move it, and the card says "Iron Fist's ATK".
        message.PreventDamage(this.attack, effect)

    def he_is_the_one_defending(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
        # Damage he takes while defending, rather than any damage aimed at him:
        # an attack that simply targets an ally is not one he defended against.
        return (
            message.would_atk_message is not None
            and message.would_atk_message.GetDefender() == effect.this
        )

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.Interrupt,
            "This",
            iron_fist,
            is_from_attack=True,
            conditions=[he_is_the_one_defending],
        ),
    ]
