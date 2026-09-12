from . import *

# * Jessica Jones


def GetAbilities() -> Sequence['Ability']:

    def tough_on_your_identity(effect: 'Effect', ui: Any) -> int:
        # Her controller's identity, whoever that is. Capped at 4 by the card.
        identity = effect.this.GetOwnerPlayer().GetIdentity()
        return min(ToughOn(identity), 4)

    return [
        AbilityFactory.CanPlayThisAllyCard(),
        AbilityFactory.ThisGainKeyword(
            tough_on_your_identity,
            thwart=1,
            change_on_event=OnEvent.Status(Identity, 'Tough'),
        ),
    ]
