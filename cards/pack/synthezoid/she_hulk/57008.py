from . import *

# Focused Rage


def GetAbilities() -> Sequence['Ability']:

    def spent_her_temper(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        this = effect.this.CastTo(Attachment)
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="She-Hulk", card_type=Leader)
        ),
        *AbilityFactory.GiveKeywordToAttached(
            "Character",
            stalwart=1,
        ),
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "AttachedCharacter",
            spent_her_temper,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            RevealThisCard,
        ),
    ]
