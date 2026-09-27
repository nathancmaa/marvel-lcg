from . import *


def GetAbilities() -> Sequence['Ability']:
    def rascal(effect: 'Effect', message: 'Message.AfterCardBecomeBoost') -> None:
        player = message.GetAgainstPlayer()
        if not player:
            return
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal this card to yourself as a facedown encounter card",
                lambda targets: player.DealEncounterCard(message.trigger, effect),
            ),
            AbilityFactory.ForChoiceAbility(
                "Spend 1 resource of any type",
            ).SetCost(Cost("1"), is_choose_ability=True),
        )

    return [
        AbilityFactory.AfterCardBecomeBoost(
            AbilityType.ForcedResponse,
            Treachery,
            rascal,
            conditions=[
                lambda effect, message:
                    message.boost_message.activating_enemy == effect.this,
            ],
        ),
        AvatarWouldBeDefeated(),
    ]
