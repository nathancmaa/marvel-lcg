from . import *

# God of War


def GetAbilities() -> Sequence['Ability']:

    def god_of_war_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        def attack_engaged_player(player: 'Player') -> 'Worlds.Enemies.ActivatedResult':
            return Worlds.Enemies.DoActivateAgainstYouInternal(
                effect,
                player,
                activate="Attack",
                include_minion="Engaged",
                include_villain=False,
            )

        result = Players.ForEachPlayer(
            effect,
            attack_engaged_player,
            Worlds.Enemies.ActivatedResult(),
        )
        if result.activated_cnt == 0:
            minion = Worlds.DiscardEncounterCardsUntil(
                effect,
                card_type=Minion,
            )
            if minion:
                minion.Reveal(message.GetToPlayer(), effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            god_of_war_revealed,
        ),
    ]
