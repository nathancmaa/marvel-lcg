from . import *

# * Two-Gun Kid: Matthew Hawk

def GetAbilities() -> Sequence['Ability']:

    def two_gun_kid(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Ally)
        Unused(this)

        for target in effect.targets:
            if not message.HasTarget(target):
                message.AddTarget(target)


    return [
        AbilityFactory.WhenUnitMakeAttack(
            AbilityType.Interrupt,
            "This",
            two_gun_kid,
            is_basic_attack=True
        ).SetTarget(
            Enemy,
            check_fn=lambda effect, face:
                not effect.GetBindMessage(Message.WhenUnitWouldAttack).HasTarget(face),
        ),
    ]
