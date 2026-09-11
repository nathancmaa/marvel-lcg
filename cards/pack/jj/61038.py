from . import *

# * Echo: Maya Lopez


def GetAbilities() -> Sequence['Ability']:

    def echo(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Ally)
        # Her own controller's identity, not whoever is dealing the damage: the
        # initiator of an incoming attack is the enemy making it. Read through
        # IsType rather than GetHero(), which asserts in alter-ego form -- an
        # ally can still be attacked while its controller is Jessica Jones.
        identity = this.GetOwnerPlayer().GetIdentity()
        if Hero.IsType(identity):
            message.ReduceDamage(identity.defense, effect)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            "This",
            echo,
            is_from_attack=True,
        ),
    ]
