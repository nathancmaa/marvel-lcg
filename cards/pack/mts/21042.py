from . import *

# In-Betweener

def GetAbilities() -> Sequence['Ability']:

    def in_betweener(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        Faces.ShuffleAllTo([this], "EncounterDeck", effect)

    def in_betweener_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        villain = Worlds.ChooseVillain(
            effect,
            prompt="Choose a villain to damage",
        )
        if villain:
            this.DealDamage([villain], 2, effect)
        Faces.RemoveAllFromGame([this], effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            in_betweener
        ).SetPlay().SetLabel(),
        AbilityFactory.WhenThisRevealed(
            None,
            in_betweener_revealed
        ).SetCannotBeCancel()
    ]

