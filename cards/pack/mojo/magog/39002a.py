from . import *

# Melee in the Mojo-seum

def GetAbilities() -> Sequence['Ability']:

    def select_random_modular_set(
        effect: 'Effect',
        message: 'Message.WhenGameBeginSetup',
    ) -> None:
        modular_sets = [
            encounter_set
            for encounter_set in message.encounter_set_names
            if not encounter_set.startswith("standard")
            and not encounter_set.startswith("expert")
        ]
        # A game already down to one modular set (older saves recorded only
        # Crime) keeps it without drawing a random number, so its replay does
        # not shift.
        if len(modular_sets) <= 1:
            return
        message.encounter_set_names = [
            encounter_set
            for encounter_set in message.encounter_set_names
            if encounter_set not in modular_sets
        ] + Rand.RandomChoice2(modular_sets, 1, effect)

    def melee_in_the_mojo_seum_revealed(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.PutIntoPlay(
            effect,
            name="The Champion",
            card_type=Environment
        )
        SetupCards.PutIntoPlay(
            effect,
            name="The Challengers",
            card_type=Environment
        )

    return [
        AbilityFactory.WhenGameBeginSetup(
            select_random_modular_set
        ),
        AbilityFactory.WhenCardSetup(
            "This",
            melee_in_the_mojo_seum_revealed
        ),
    ]

