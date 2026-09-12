from . import *

# Just Passing Through


def GetAbilities() -> Sequence['Ability']:

    def just_passing_through(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        if not player:
            return
        identity = player.GetIdentity()
        # "confuses their identity. Otherwise, they stun their identity" -- the
        # fallback is for an identity that cannot be confused.
        if not Faces.GiveStatus([identity], "Confused", effect):
            Faces.GiveStatus([identity], "Stunned", effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            just_passing_through,
            has_defeating_player=True,
        ),
    ]
