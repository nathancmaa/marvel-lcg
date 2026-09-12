from . import *

# * Hulk: Bruce Banner

RAGE_COUNTER = "rage"


def GetAbilities() -> Sequence['Ability']:

    def take_it_personally(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        this = effect.this.CastTo(Ally)
        Faces.PlaceCountersOn([this], 1, RAGE_COUNTER, effect)

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.ThisGainKeyword(
            lambda effect, ui:
                effect.this.CastTo(Ally).GetCounters(RAGE_COUNTER),
            attack=1,
            change_on_event=OnEvent.Counter("This", RAGE_COUNTER),
        ),
        # "After the villain attacks you" -- you, not Hulk. He is angered by
        # what happens to his controller, and counts nothing when the villain
        # goes after somebody else.
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.Response,
            Villain,
            "You",
            take_it_personally,
        ),
    ]
