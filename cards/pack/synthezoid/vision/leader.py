from . import *


def VisionLeaderAbilities(*, stage_two: bool) -> Sequence['Ability']:
    """Vision, in all four of his stages.

    His whole set turns on which way his mass form attachment is lying, and it
    turns over on its own once a round -- after threat goes on the main scheme,
    before he activates.
    """

    def give_him_his_form(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(Leader)
        Find.FindAndAttachTo(
            effect,
            this,
            who_perform=Worlds.GetEnemyTeam(effect),
            name=DENSE,
        )

    def he_arrives(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Leader)
        Utility.DealEachPlayerEncounterCard(effect)
        Utility.CannotTakeDamageThisPhase(this, effect)

    def phase_shift(effect: 'Effect', message: 'Message.AfterResolveVillainPhaseStep') -> None:
        FlipMassForm(effect)

    opening: 'Ability' = (
        AbilityFactory.WhenThisRevealed(
            None,
            he_arrives,
        )
        if stage_two else
        AbilityFactory.WhenCardSetup(
            "This",
            give_him_his_form,
        )
    )

    return [
        opening,
        # Step 1 is the main scheme placing threat, so he has already picked a
        # side by the time he activates in step 2.
        AbilityFactory.AfterResolveVillainPhaseStep(
            AbilityType.ForcedResponse,
            1,
            phase_shift,
        ),
    ]
