from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Faces.GiveStatus([message.GetToPlayer().GetIdentity()], "Confused", effect)

    def discard_and_attack(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this
        Unused(message)
        player = effect.GetInitiator()
        Faces.DiscardAll([this], effect)
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.DoAttackYou(player, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        identity = message.GetToPlayer().GetIdentity()
        if identity.IsConfused():
            effect.this.PlaceThreatOnSchemes("MainScheme", 1, effect)
        else:
            Faces.GiveStatus([identity], "Confused", effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(KINGPIN),
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            discard_and_attack,
        ).SetCostFunc(CostFunc.Discard("YourHandCards", trait="ATTACK", card_type=Event))
        .SetName("Discard an ATTACK event → discard Vanessa Fisk and Kingpin attacks you")
        .AnyPlayerCanDoThis(),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
