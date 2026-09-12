from cards.pack.synthezoid import *


def ScarletTwinAbilities(fallback: Callable[['Player', 'Effect'], None]) -> Sequence['Ability']:
    """Speed and Wiccan, both printed "do this to you, otherwise do that".

    The first half of each is a competitive instruction aimed at the opposing
    player; cooperatively it is the second half that lands.
    """

    def run(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = Worlds.GetYourTeamLeader(effect)
        if leader:
            assert False
        player = message.GetToPlayer()
        if player:
            fallback(player, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            run,
        ),
    ]
