from . import *

# Sensory Overload


def GetAbilities() -> Sequence['Ability']:

    def holder(effect: 'Effect') -> 'Player|None':
        # An encounter card's effect can have the villain as its initiator
        # (it asserted against Purple Man), so "you" is the player whose
        # play area holds this obligation.
        return effect.this.card.area.play_area

    def sensory_overload(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        player = holder(effect)
        if player:
            player.GetIdentity().TakeDamage(effect.this, 1, effect)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            CardFinder(trait="SENSE"),
            sensory_overload,
            conditions=[
                lambda effect, message:
                    holder(effect) is not None
                    and message.trigger.GetOwnerPlayer() == holder(effect)
            ],
        ),
        AbilityFactory.AfterUnitRecovery(
            AbilityType.AlterEgoResponse,
            "You",
            DiscardThisCard,
        ),
    ]
