from . import *

# One-Two Punch


def GetAbilities() -> Sequence['Ability']:

    def she_hulk(effect: 'Effect') -> 'CardFace|None':
        return Worlds.FindCardOnField(effect, name="She-Hulk", card_type=Leader)

    def one_two_punch_alter_ego(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = she_hulk(effect)
        player = message.GetToPlayer()
        if leader and player:
            leader.CastTo(Leader).DoSchemes(player, effect)
            Faces.GiveStatus([leader], "Tough", effect)

    def one_two_punch_hero(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = she_hulk(effect)
        player = message.GetToPlayer()
        if leader and player:
            leader.CastTo(Leader).DoAttackYou(player, effect)
            Faces.GiveStatus([leader], "Tough", effect)

    return [
        AbilityFactory.WhenThisRevealed(
            "Alter-Ego",
            one_two_punch_alter_ego,
        ),
        AbilityFactory.WhenThisRevealed(
            "Hero",
            one_two_punch_hero,
        ),
    ]
