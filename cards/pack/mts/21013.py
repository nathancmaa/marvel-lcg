from . import *

# * White Tiger: Ava Ayala

def GetAbilities() -> Sequence['Ability']:

    def white_tiger(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Ally)
        Unused(this)

        villain = Worlds.ChooseVillain(
            effect,
            prompt="Choose a villain for White Tiger's stage value",
        )
        value = villain.printed_stage if villain else 0
        value = Math.MinMax(value, 1, 3)
        for target in effect.targets:
            player = target.GetControlByPlayer()
            player.DrawUp(value, effect)


    return [
        AbilityFactory.AfterYouPlayThisFromHand(
            AbilityType.Response,
            white_tiger,
        ).SetTarget("Initiator"),
    ]

