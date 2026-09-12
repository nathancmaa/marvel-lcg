from . import *

# Observe


def GetAbilities() -> Sequence['Ability']:

    def observe(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        initiator = effect.GetInitiator()
        for target in effect.targets:
            target.CastTo(Villain).DoSchemes(initiator, effect)
        # After the scheming, not before: you take the threat and then brace.
        Faces.GiveStatus([initiator.GetIdentity()], "Tough", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            observe,
        ).SetPlay().SetLabel()
        .SetTarget(Villain),
    ]
