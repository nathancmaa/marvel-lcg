from cards.pack import *


def FindBullseye(effect: 'Effect', player: 'Player') -> 'Minion|None':
    return Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        name="Bullseye",
        card_type=Minion,
    )


def BullseyeInPlay(effect: 'Effect', player: 'Player') -> 'Minion|Villain|None':
    """Bullseye at ``player``'s table: Daredevil's nemesis minion, or the
    Bullseye villain of Fear No Evil's underling set.

    Not a by-name finder: the referential rules would narrow "Bullseye" on
    a nemesis card to the nemesis minion, and the villain is a unique
    Bullseye that keeps that minion from entering play at all. Against the
    villain the attack option would then never be offered.
    """
    game_area = player.GetIdentity().card.game_area
    for face in Worlds.GetOnFieldCards(effect):
        if (Minion.IsType(face) or Villain.IsType(face)) and face.IsName("Bullseye") and face.card.game_area == game_area:
            return face.CastTo(Minion|Villain)
    return None
