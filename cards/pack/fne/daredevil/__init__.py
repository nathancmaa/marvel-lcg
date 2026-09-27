from cards.pack import *


SENSE_DECK = "daredevil_sense"
SENSE_CARD_IDS = ["60002", "60003", "60004", "60005", "60006"]


def GetSenseDeck(player: 'Player') -> 'Deck|None':
    return player.special_decks.get(SENSE_DECK)


def RevealSenseDeck(top: 'CardFace', effect: 'Effect') -> None:
    Unused(top)
    sense_deck = GetSenseDeck(effect.GetInitiator())
    if not sense_deck:
        return

    # The Sense deck has a fixed, inspectable order. Every card is faceup,
    # although Daredevil's Superhuman Senses can play only its top card.
    for sense in sense_deck.GetAll():
        sense.card.can_state.is_like_in_hand = None
        sense.FlipTo(effect, face_up=True, ui_look_at=False)


def SetupSenseDeck(effect: 'Effect', message: 'Message.WhenPlayerSelectHero') -> None:
    from game.message import Message

    player = effect.GetInitiator()
    if GetSenseDeck(player):
        return

    sense_deck = Deck2(player, DeckType.AdditionalDeck, CardFace)
    player.special_decks[SENSE_DECK] = sense_deck

    senses = CardFinder(trait="SENSE").Checks(player.set_aside_deck.Get())
    Faces.MoveAllTo(senses, sense_deck, effect)
    Message.WhenDeckCreated_Text(sense_deck)
    sense_deck.Shuffle(effect)


def ReturnSenseCardsToDeck() -> Sequence['Ability']:
    def return_sense_to_deck(effect: 'Effect', message: 'Message.WhenCardWouldLeavePlay') -> None:
        deck = GetSenseDeck(effect.GetInitiator())
        if not deck or message.into_area == deck:
            return

        message.SetBeInstead(effect)
        Faces.MoveAllToDeck([message.trigger], deck, "Bottom", effect)

    return [
        AbilityFactory.WhenCardWouldLeavePlay(
            AbilityType.ForcedInterrupt,
            CardFinder(trait="SENSE"),
            return_sense_to_deck,
            conditions=[
                lambda effect, message:
                    message.trigger.GetOwnerPlayer() == effect.GetInitiator()
            ],
        ),
    ]


def GetAttachedUpgradeCount(face: 'CardFace') -> int:
    return len(face.GetInventoryDeck().FindCards(card_type=Upgrade))


def ChooseAndPlaySense(player: 'Player', effect: 'Effect', *, optional: bool=True) -> 'CardFace|None':
    sense_deck = GetSenseDeck(player)
    if not sense_deck:
        return None

    faces = sense_deck.GetAll(from_top=True, include_removed=False)
    if optional:
        face = player.MayChooseFace(faces, effect, not_move=True)
    else:
        face = player.AskChooseFace(
            faces,
            effect,
            prompt="Choose a Sense upgrade to play",
        )
    if face:
        played = player.PlayCardsLikeInTurn(
            [face],
            effect,
            ignore_resources_cost=True,
            forced=True,
            if_not_play_discard_it=False,
        )
        return played[0] if played else None
    return None


def SenseCanAttachToEnemyOrScheme() -> 'Ability':
    return AbilityFactory.CanPlayThisUpgradeCard(
        CardFinder(card_type=Enemy|Scheme2)
    )


def SenseCompletedByYou(effect: 'Effect', face: 'CardFace|None') -> bool:
    """Whether ``face`` counts as "you" for a Sense interrupt.

    Your identity, or a card you play or control that is not a character
    (an event's damage or threat removal). An ally defeating the enemy or
    thwarting the scheme is not you.
    """
    if face is None or Ally.IsType(face):
        return False
    if Condition.CheckWhichCard("YourIdentity", face, effect):
        return True
    return not Unit2.IsType(face) and face.GetControlByOrOwner() == effect.this.GetOwnerPlayer()


def SenseCompletionAbilities(operation: Callable[['Effect', 'Message2'], None]) -> Sequence['Ability']:
    """"When you defeat attached enemy or remove the last threat from
    attached scheme, discard this card → ..."

    Both are interrupts before the event: the enemy would be defeated (the
    upgrade would otherwise be discarded with it, before a When Defeated
    ability runs) or threat would be removed that leaves none. Discarding
    the Sense returns it to the bottom of the Sense deck, so it can be put
    back into play straight away, as Focus the Senses does when defeated.
    """

    def you_would_defeat(effect: 'Effect', message: 'Message.WhenUnitWouldBeDefeated') -> bool:
        return not message.is_be_instead and SenseCompletedByYou(effect, message.killer)

    def you_would_remove_last_threat(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
        return (
            not message.is_be_instead
            and not message.cannot_be_removed
            and 0 < message.trigger.CastTo(Scheme2).threat <= message.value
            and SenseCompletedByYou(effect, message.by_face)
        )

    def discard_then(effect: 'Effect', message: 'Message2') -> None:
        # Not a CostFunc.Discard: Matt Murdock's Forced Interrupt replaces
        # the discard with the bottom of the Sense deck, which a discard
        # cost counts as unpaid, and the effect would never resolve.
        Faces.DiscardAll([effect.this], effect)
        operation(effect, message)

    return [
        AbilityFactory.WhenUnitWouldBeDefeated(
            AbilityType.Interrupt,
            "AttachedEnemy",
            discard_then,
            conditions=[you_would_defeat],
        ),
        AbilityFactory.WhenSchemeWouldRemoveThreat(
            AbilityType.Interrupt,
            "AttachedScheme",
            discard_then,
            conditions=[you_would_remove_last_threat],
        ),
    ]
