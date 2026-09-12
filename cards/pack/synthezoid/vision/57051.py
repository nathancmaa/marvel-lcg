from . import *

# Solar Beam


def GetAbilities() -> Sequence['Ability']:

    def vision(effect: 'Effect') -> 'Leader|None':
        face = Worlds.FindCardOnField(effect, name="Vision", card_type=Leader)
        return face.CastTo(Leader) if face else None

    def solar_beam_alter_ego(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = vision(effect)
        player = message.GetToPlayer()
        if not leader or not player:
            return
        bonus = 1 if MassFormIs(effect, INTANGIBLE) else 0
        leader.DoSchemes(player, effect, property=SchemeProperty(additional_value=bonus))

    def solar_beam_hero(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        leader = vision(effect)
        player = message.GetToPlayer()
        if not leader or not player:
            return
        bonus = 1 if MassFormIs(effect, DENSE) else 0
        leader.DoAttackYou(player, effect, property=AttackProperty(additional_value=bonus))

    return [
        AbilityFactory.WhenThisRevealed(
            "Alter-Ego",
            solar_beam_alter_ego,
        ),
        AbilityFactory.WhenThisRevealed(
            "Hero",
            solar_beam_hero,
        ),
    ]
