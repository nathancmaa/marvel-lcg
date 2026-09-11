from . import *

from game.card.face.attribute.can_thwart import ThwartProperty

# Grapnel Launcher


def GetAbilities() -> Sequence['Ability']:

    def grapnel_launcher(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        hero = effect.GetInitiator().GetHero()
        # A real basic thwart rather than a bare removal of threat, so anything
        # watching for one still fires -- but without the exhaust cost, which is
        # what lets an exhausted hero use it.
        hero.BasicThwart(
            list(effect.targets),
            effect,
            property=ThwartProperty(is_basic_power=True, additional_value=1),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            grapnel_launcher,
        ).SetCostFunc(CostFunc.Discard("This"))
        .SetLabel("thwart")
        .SetTarget(Scheme2)
        .SetIgnoreKeyword('Crisis', 'Patrol'),
    ]
