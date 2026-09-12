from . import *

# Teenage Superheroes


def GetAbilities() -> Sequence['Ability']:

    def teenage_superheroes(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        if not player:
            return
        minions = Worlds.GetOnFieldMinions(effect)
        resolved = Faces.ResolveAbility(minions, player, AbilityType.WhenRevealed, effect)
        # An empty board, or a board of minions with nothing to say.
        if not resolved:
            this.GainSurge(1, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            teenage_superheroes,
        ),
    ]
