from cards.pack.synthezoid import *


def ThunderboltAbilities(hit: Callable[['Player', 'Effect'], None],
                         boost_hit: Callable[['Player', 'Effect'], None]|None=None,
                         ) -> Sequence['Ability']:
    """The three Thunderbolts, who all read the same way.

    Each is printed "do this to your leader, otherwise do that to you". The
    players have no leader of their own here, so it is always the second half --
    see Worlds.GetYourTeamLeader, which is None by construction in this fork.
    """

    def against_the_player(handler: Callable[['Player', 'Effect'], None]):
        def run(effect: 'Effect', message: 'Message2') -> None:
            leader = Worlds.GetYourTeamLeader(effect)
            if leader:
                assert False
            player = message.GetToPlayer()
            if player:
                handler(player, effect)
        return run

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            against_the_player(hit),
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            against_the_player(boost_hit or hit),
        ),
    ]
