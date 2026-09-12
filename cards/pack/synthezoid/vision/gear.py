from . import *


def VisionGearAbilities(cost: 'Cost', **keywords: int) -> Sequence['Ability']:
    """Solar Gem and Vision's Cape, which differ only in what they grant.

    Both hang on Vision, both give him something, and both come off the same
    way: hit him with a basic attack, pay the two resources, and he flips.
    """

    def shake_it_loose(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        this = effect.this.CastTo(Attachment)
        Faces.DiscardAll([this], effect)
        FlipMassForm(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Vision", card_type=Leader),
        ),
        *AbilityFactory.GiveKeywordToAttached(
            "Character",
            **keywords,
        ),
        # Against Vision specifically, and only a basic attack: the card asks
        # you to hit him yourself rather than to play something at him.
        AbilityFactory.AfterUnitAttackEnd(
            AbilityType.HeroResponse,
            "YourHero",
            shake_it_loose,
            is_basic_attack=True,
            damaged_who="AttachedCharacter",
        ).SetCostFunc(CostFunc.Spend(cost)),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            RevealThisCard,
        ),
    ]
