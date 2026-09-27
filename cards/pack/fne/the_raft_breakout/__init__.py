from cards.pack import *


def ActivationBoostCards(message: 'Message.AfterUnitAttackEnd') -> List['CardFace']:
    """Every boost card dealt for the attacks this activation made."""
    cards: List['CardFace'] = []
    for attack in message.atk_messages:
        cards.extend(attack.boost_faces)
    return Types.RemoveDuplicates(cards)
