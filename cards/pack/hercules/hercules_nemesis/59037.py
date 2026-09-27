from . import *

# * Lernean Hydra


def GetAbilities() -> Sequence['Ability']:

    def lernean_hydra_damaged(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        this = effect.this.CastTo(Minion)
        player = message.attacker.GetControlByPlayer()
        heal_hydra = AbilityFactory.ForChoiceAbility(
            "Lernean Hydra heals 2 damage",
            lambda targets:
                this.HealthUnits([this], 2, effect),
        )
        spend_physical = AbilityFactory.ForChoiceAbility(
            "Spend a [physical] resource",
        ).SetCost(
            Cost("R"),
            is_choose_ability=True,
        )
        player.ChooseAbilities(
            effect,
            heal_hydra,
            spend_physical,
        )

    return [
        AbilityFactory.AfterUnitAttackEnd(
            AbilityType.ForcedResponse,
            Friend,
            lernean_hydra_damaged,
            damaged_who="This",
        ),
    ]
