from . import *


def SheHulkLeaderAbilities(*, stage_two: bool) -> Sequence['Ability']:
    """She-Hulk, in all four of her stages.

    Stages I and III open by arming her; II and IV open by hitting the table
    and going untouchable for the phase. The forced response is printed on all
    four, so it is written once here rather than four times over.
    """

    def arm_her(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(Leader)
        Find.FindAndAttachTo(
            effect,
            this,
            who_perform=Worlds.GetEnemyTeam(effect),
            name="Superhuman Strength",
        )

    def she_arrives(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Leader)
        Utility.DealEachPlayerEncounterCard(effect)
        Utility.CannotTakeDamageThisPhase(this, effect)

    def punish_the_change(effect: 'Effect', message: 'Message.AfterUnitChangeForm') -> None:
        this = effect.this.CastTo(Leader)
        # "that hero" -- the one who just flipped up, not whoever is taking a
        # turn. In two-handed play those are not always the same seat.
        this.DealDamage([message.trigger], 1, effect)

    opening: 'Ability' = (
        AbilityFactory.WhenThisRevealed(
            None,
            she_arrives,
        )
        if stage_two else
        AbilityFactory.WhenCardSetup(
            "This",
            arm_her,
        )
    )

    return [
        opening,
        # Any identity flipping up, not this card's own form: She-Hulk is a
        # leader and has none.
        AbilityFactory.AfterUnitChangeForm(
            AbilityType.ForcedResponse,
            Identity,
            punish_the_change,
            to_form=Hero,
        ),
    ]
