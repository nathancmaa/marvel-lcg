from . import *

# Crime Scene Investigation

def GetAbilities() -> Sequence['Ability']:

    def block_removal_except_for_main_scheme_completion_reset(
        effect: 'Effect',
        message: 'Message.WhenSchemeWouldRemoveThreat',
    ) -> bool:
        Unused(effect)
        by_effect = message.by_effect
        completion_message = by_effect.bind_message
        completion_event = Message.WhenMainSchemeStageWouldBeCompleted
        # Normal advancement discards the old stage. Only allow a main
        # scheme's own "instead of advancing" completion reset.
        is_main_scheme_completion_reset = (
            MainScheme.IsType(message.trigger)
            and message.trigger == by_effect.this
            and by_effect.ability.when == completion_event
            and completion_message is not None
            and completion_message.is_be_instead
        )
        return not is_main_scheme_completion_reset

    def crime_scene_investigation(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        Unused(this)

        num = effect.GetPaidResources().GetColor("B")
        this.RemoveThreatFromSchemes([this], num, effect)


    return [
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            Scheme2,
            not_from_this_effect=True,
            conditions=[
                block_removal_except_for_main_scheme_completion_reset
            ],
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            crime_scene_investigation
        ).SetCost(Cost("B")),
    ]

