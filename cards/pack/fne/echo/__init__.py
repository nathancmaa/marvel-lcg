from cards.pack import *


def IsAspectOrBasicEvent(face: 'CardFace') -> bool:
    return Event.IsType(face) and (face.IsClass("Basic") or face.GetAspect() is not None)


def FindKingpin(effect: 'Effect', player: 'Player') -> 'Minion|None':
    face = Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        name="Kingpin",
        card_type=Minion,
    )
    return face


def PutKingpinIntoPlay(effect: 'Effect', player: 'Player') -> 'Minion|None':
    kingpin = FindKingpin(effect, player)
    if kingpin:
        kingpin.PutIntoPlay(player, effect)
    return kingpin


def PhotographicReflexesInHand(player: 'Player') -> List['CardFace']:
    return player.hand_cards.FindCards(name="Photographic Reflexes", card_type=Event)


def IsPlayingTuckedEvent(player: 'Player', play_effect: 'Effect') -> bool:
    """Whether ``play_effect`` plays an event tucked under ``player``'s Echo."""
    tucked_area = player.GetIdentity().GetPlacedCardArea()
    return (
        play_effect.this.card.area == tucked_area or
        play_effect.context.declared_play_from_area == tucked_area
    )


def SpareReflexes(player: 'Player', play_effect: 'Effect') -> List['CardFace']:
    """Reflexes copies in hand that are not among ``play_effect``'s payment.

    The resources for a play are chosen with the play itself, before any
    card resolves, so the copy to discard must be one the player kept back.
    """
    paying = {pay_effect.this for pay_effect in play_effect.context.paid_this_res_effects}
    return [face for face in PhotographicReflexesInHand(player) if face not in paying]
