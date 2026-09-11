from cards.pack.synthezoid import *


def RoyalGuardAbilities() -> Sequence['Ability']:
    """Janus and Amir, who read identically.

    Both come for whoever is carrying Blood Debt and settle for thinning the
    deck of anyone who is not.
    """

    def royal_guard(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetToPlayer()
        if not player:
            return
        if player.GetIdentity().HasTrait("HUNTED"):
            this.DoActivate(player, effect)
        else:
            player.DiscardDeckTopCards(2, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            royal_guard,
        ),
    ]
