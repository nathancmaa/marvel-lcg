from . import *

# * Mad Jack's Platform


def GetAbilities() -> Sequence['Ability']:

    def no_one_to_carry_it(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        # "Attach to a minion of the enemy team's choice" -- if there is no
        # minion to put it on, the platform is just another card going past.
        if not Worlds.GetOnFieldMinions(effect):
            this.GainSurge(1, effect)

    def platform_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()
        if not player:
            return
        minions = player.GetEngagedMinions()
        if minions:
            this.PutIntoPlay(player, effect)
            this.AttachTo2(minions[0], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(card_type=Minion),
        ),
        *AbilityFactory.GiveKeywordToAttached(
            Minion,
            health=4,
            stalwart=1,
        ),
        AbilityFactory.WhenThisRevealed(
            None,
            no_one_to_carry_it,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            platform_boost,
        ),
    ]
