from . import *

# * Run Them to Ground


def GetAbilities() -> Sequence['Ability']:

    def run_them_to_ground(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        world = effect.world

        # Skip the next villain phase.
        world.skip_villain_phase_count += 1

        # Deal each player 1 facedown encounter card, now rather than at the
        # usual point of the phase -- which is the whole point of the clause,
        # since the phase that would have dealt them is the one being skipped.
        Players.ForEachPlayer(effect, lambda player: player.DealEncounterCards(1, effect))

        villain = Worlds.FindVillain(effect)
        if not villain:
            return

        immunity = villain.effect.RegisterTemp(
            AbilityFactory.UnitCannotTakeDamageWhile(
                AbilityType.NonKeyword,
                "This",
            ),
            unregister_after_exec=False,
        )

        # Released at the start of the next villain phase that actually
        # happens. A skipped phase still opens, so the counter is what tells
        # the two apart: it is decremented after this message is sent, so a
        # phase about to be skipped still reads as one owed.
        villain.effect.RegisterTemp(
            AbilityFactory.WhenVillainPhaseBegin(
                AbilityType.Temp2,
                lambda release_effect, release_message: Effects.UnRegister(immunity),
                conditions=[
                    lambda release_effect, release_message:
                        release_effect.world.skip_villain_phase_count == 0,
                ],
            ),
            unregister_after_exec=True,
        )

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            run_them_to_ground,
        ),
    ]
