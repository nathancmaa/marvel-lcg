from . import *

# Black Belt


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.CanPlayThisUpgradeCard(
            Friend,
            conditions=[
                # Any player's MARTIAL ARTIST card, in play or in hand -- the
                # card says "controls", which is the board rather than the deck.
                lambda effect, message:
                    bool(Worlds.FindCardsOnField(
                        effect, finder=CardFinder(trait="MARTIAL ARTIST"),
                    )),
            ],
        ),
        *AbilityFactory.GiveKeywordToAttached(
            Friend,
            health=1,
            trait="MARTIAL ARTIST",
        ),
    ]
