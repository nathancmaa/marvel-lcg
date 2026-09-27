from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        minions = Worlds.GetEncounterDiscardPileCards(
            effect,
            CardFinder(card_type=Minion),
        )
        if minions:
            Filter.One(minions, effect).Reveal(message.GetToPlayer(), effect)
        else:
            scheme = Worlds.FindMainScheme(effect)
            if scheme:
                scheme.PlaceThreatOnSchemes([scheme], 3, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        scheme = Worlds.FindMainScheme(effect)
        if scheme:
            scheme.PlaceThreatOnSchemes(
                [scheme],
                len(player.GetControlCharacters()),
                effect,
            )

    return [
        AbilityFactory.IfExpertModeThisGainKeyword(incite=1),
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
