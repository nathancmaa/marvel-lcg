from . import *


def GetAbilities() -> Sequence['Ability']:
    def discard_and_shatter(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Unused(message)
        PlaceShatterCountersOnTheAvatarOfLokivillain(1, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            "YourIdentity",
            when_attach_exhaust_attached=True,
        ),
        *AbilityFactory.CardCannotReady("AttachedIdentity"),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
            ex_operation=discard_and_shatter,
        ).SetCost(Cost("2", same_type=True)),
    ]
