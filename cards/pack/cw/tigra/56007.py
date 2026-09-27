from . import *

# Hunted

def GetAbilities() -> Sequence['Ability']:

    def hunted_cost(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        faces = effect.cost_func.Get(CostFunc.SearchForCard).searched_faces
        if faces:
            this.AttachTo2(faces[0], effect)
            if faces[0].IsInPlay():
                Faces.GiveStatus(faces, "Stunned", effect)

        # Entry responses can defeat the minion while paying the additional
        # cost, before Hunted attaches. Do not leave it in the processing area.
        if this.IsInProcessingArea():
            Faces.DiscardAll([this], effect)

    def hunted(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        Faces.ReadyAll(effect.targets, effect)


    return [
        AbilityFactory.CanPlayThisUpgradeCard(
            replaced_operation=hunted_cost
        ).SetCostFunc(CostFunc.SearchForCard(Minion, "PutIntoPlayEngagedYou", include_encounter_deck=True, include_encounter_discard_pile=True)),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.Interrupt,
            "AttachedMinion",
            hunted
        ).SetTarget(name="Tigra", canbe_ready=True),
    ]

