from . import *

# Photographic Reflexes is implemented by Echo (60037a), because the tucked
# event must keep its own Action/Interrupt/Response timing window. This card
# only limits its own use as a resource: the copy discarded to play a tucked
# event cannot also pay for that event.


def GetAbilities() -> Sequence['Ability']:

    def can_pay(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
        player = message.GetToPlayer()
        if not IsPlayingTuckedEvent(player, message.paying_for_effect):
            return True
        # Another copy must stay in hand to be discarded for the play. With
        # two or more, the play itself checks that the player kept one back
        # (Echo's discount needs a copy that is not paying).
        return len(PhotographicReflexesInHand(player)) >= 2

    drop_pay = AbilityFactory.CheckThisCanDropPay()
    drop_pay.conditions.insert(0, can_pay)
    return [drop_pay]
