from . import *

# * Luke Cage, alter-ego


def GetAbilities() -> Sequence['Ability']:

    def find_the_process(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        initiator = effect.GetInitiator()
        face = Search.PlayerCard(
            effect,
            initiator,
            include_player_deck=True,
            include_discard_pile=True,
            name=BURSTEIN_PROCESS,
            card_type=Upgrade,
        )
        if face:
            initiator.GainCard(face, effect)

    return [
        # Unbreakable Skin is printed on both faces, so it holds in alter-ego
        # form too -- the tough cards do not come off when he flips.
        AbilityFactory.ThisCanHaveAdditionalTough("Any"),
        AbilityFactory.UnitAttackGainKeyword(
            None,
            "This",
            lost_piercing=True,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            find_the_process,
        ).LimitOncePerPhase(),
    ]
