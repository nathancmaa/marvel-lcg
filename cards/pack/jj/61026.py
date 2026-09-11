from . import *

# Joys of Life


def GetAbilities() -> Sequence['Ability']:

    def joys_of_life(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust a CIVILIAN alter-ego to ready a hero or ally",
                lambda targets: Faces.ReadyAll(targets, effect),
            ).SetTarget(Hero | Ally, canbe_ready=True)
            .SetCostFunc(CostFunc.Exhaust(card_type=AlterEgo, trait="CIVILIAN")),
            AbilityFactory.ForChoiceAbility(
                "Exhaust a hero or ally to ready a CIVILIAN alter-ego",
                lambda targets: Faces.ReadyAll(targets, effect),
            ).SetTarget(AlterEgo, trait="CIVILIAN", canbe_ready=True)
            .SetCostFunc(CostFunc.Exhaust(card_type=Hero | Ally)),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            joys_of_life,
        ).SetPlay().SetLabel(),
    ]
