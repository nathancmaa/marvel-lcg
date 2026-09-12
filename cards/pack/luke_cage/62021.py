from . import *

# * She-Hulk: Jennifer Walters


def GetAbilities() -> Sequence['Ability']:

    def she_hulk(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        identity = effect.this.GetOwnerPlayer().GetIdentity()
        Faces.GiveStatus([identity], "Tough", effect)

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.Response,
            "This",
            she_hulk,
        ),
    ]
