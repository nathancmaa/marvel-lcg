from . import *

# * Hellcat: Patsy Walker


def GetAbilities() -> Sequence['Ability']:

    def hellcat(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Ally)
        initiator = effect.GetInitiator()
        this.PutIntoPlay(initiator, effect, under_control=True)

        def at_the_end_of_the_phase():
            # She may have gone already -- defeated, or discarded by something
            # else -- and discarding a card that is no longer in play would be
            # discarding it twice.
            if this.IsInPlay():
                Faces.DiscardAll([this], effect)

        RunAt.TheEndOfThePhase(effect, at_the_end_of_the_phase)

    def your_identity_is_a_defender(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
        return effect.GetInitiator().GetIdentity().HasTrait("DEFENDER")

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        # The card only gains this action while your identity is a DEFENDER, so
        # the trait is checked when the action is offered rather than when the
        # card is played: Jessica Jones is one, and most heroes are not.
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            hellcat,
            conditions=[your_identity_is_a_defender],
        ).CanWorkOnlyInHand(),
    ]
