from . import *

# * Going Undercover

def GetAbilities() -> Sequence['Ability']:

    def going_undercover(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(PlayerSideScheme)
        Unused(this)

        player = message.GetDefeatingPlayer()

        faces = player.LookAtDeck("EncounterDeck", 5, effect)
        non_scenario_specific_faces = CardFinder(is_scenario_specific=False).Checks(faces, effect)
        selected: List[CardFace] = []

        def action(targets: Sequence[CardFace]):
            selected.extend(targets)
            Faces.AddToVictoryDisplay(targets, effect)

        player.MayChooseOneAbility(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Add 1 non-scenario-specific card from among those to the victory display",
                action
            ).SetTarget(non_scenario_specific_faces, not_move=True)
        )

        rest = [x for x in faces if x not in selected]
        player.PlaceOnTopAndOrBottomInAnyOrder(rest, effect)


    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            going_undercover,
            has_defeating_player=True
        ),
    ]
