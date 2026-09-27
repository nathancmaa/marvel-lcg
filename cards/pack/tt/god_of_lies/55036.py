from . import *


def GetAbilities() -> Sequence['Ability']:
    def discard_scepter(effect: 'Effect', message: 'Message.AfterCardRevealed') -> None:
        Unused(message)
        Faces.DiscardAll([effect.this], effect)

    def treachery_cannot_be_canceled(
        effect: 'Effect',
        message: 'Message.CheckIfEffectCanBeCancelBy',
    ) -> None:
        message.SetCannotBeThwart(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(AVATAR_OF_LOKI),
        *AbilityFactory.GiveKeywordToAttached(
            AVATAR_OF_LOKI,
            stalwart=1,
        ),
        Ability(
            AbilityType.NonKeyword,
            Message.CheckIfEffectCanBeCancelBy,
            [
                lambda effect, message:
                    Treachery.IsType(message.check_effect.this),
            ],
            treachery_cannot_be_canceled,
        ),
        AbilityFactory.AfterYouResolveTreachery(
            AbilityType.HeroResponse,
            discard_scepter,
        ).SetCost(Cost("2", same_type=True)).AnyPlayerCanDoThis(),
    ]
