from cards.pack import *


CAMPAIGN_ID = "age_of_apocalypse"
MISSION_ALLY_FLAG = "Age of Apocalypse next ally to mission P{}"
MISSION_ATTEMPT_FLAG = "Age of Apocalypse resolving mission attempt"


def GetMissionArea(effect: 'Effect') -> 'Deck':
    return Worlds.ScenarioArea(effect, "MissionArea")


def GetMissionScheme(effect: 'Effect') -> 'EncounterSideScheme|None':
    faces = effect.world.area_schemes_side.FindCards(
        card_type=EncounterSideScheme,
        trait="MISSION",
    )
    return faces[0] if faces else None


def HasActiveMission(effect: 'Effect') -> bool:
    return (
        Worlds.IsCampaignSelected(effect, CAMPAIGN_ID) and
        GetMissionScheme(effect) is not None
    )


def GetMissionAllies(effect: 'Effect') -> List['Ally']:
    return GetMissionArea(effect).FindCards(card_type=Ally)


def GetMissionMinions(effect: 'Effect') -> List['Minion']:
    return GetMissionArea(effect).FindCards(card_type=Minion)


def GetMissionTeam(effect: 'Effect') -> 'Support|None':
    for support in Worlds.GetOnFieldSupports(effect):
        if support.IsName("Mission Team"):
            return support
    return None


def MissionAllyFlag(player: 'Player') -> str:
    return MISSION_ALLY_FLAG.format(player.player_id)


def MustPlayNextAllyToMission(player: 'Player', effect: 'Effect') -> bool:
    from game.operate.store import Stores

    flag = MissionAllyFlag(player)
    if not Stores.HasKey(flag, effect) or Stores.GetStr(flag, effect) != "1":
        return False
    Stores.SetStr(flag, "0", effect)
    return True


def PlayAllyToMission(ally: 'Ally', player: 'Player', effect: 'Effect') -> None:
    ally.card.SetOwner(player)
    Faces.MoveAllTo(
        [ally], GetMissionArea(effect), effect,
        # Blank after the ally resets, but before enter-play abilities fire.
        before_enter_play=lambda face: face.TreatAsIfBlankInternal(1, effect),
    )


def ReduceNextMissionAllyCost(player: 'Player', effect: 'Effect') -> None:
    from game.operate.store import Stores

    Stores.SetStr(MissionAllyFlag(player), "1", effect)
    Worlds.UpdateNextCardPlayCost(
        player,
        -2,
        effect,
        finder=CardFinder(card_type=Ally),
        in_this="Phase",
    )


def ClearMissionAllyFlags(effect: 'Effect') -> None:
    from game.operate.store import Stores

    for player in Worlds.GetPlayers(effect):
        Stores.SetStr(MissionAllyFlag(player), "0", effect)


def _resource_icons(card: 'CardFace') -> Set[str]:
    resources = card.printed_resource_internal
    return {
        resource for resource in Resources.RBYG_LIST
        if resources.HasColorPrinted(resource)
    }


def _matching_resources(ally: 'Ally', card: 'CardFace') -> List[str]:
    ally_res = ally.printed_resource_internal
    card_res = card.printed_resource_internal
    matches: List[str] = []

    for resource in Resources.RBYG_LIST:
        ally_matches = ally_res.HasColorPrinted(resource) or ally_res.g > 0
        card_matches = card_res.HasColorPrinted(resource) or card_res.g > 0
        if ally_matches and card_matches:
            matches.append(resource)
    return matches


def _resolve_overseer_discard_effects(
    cards: Sequence['CardFace'],
    player: 'Player',
    mission: 'EncounterSideScheme',
    effect: 'Effect',
) -> List['CardFace']:
    """Resolve the Overseer's response before assigning discarded cards."""
    remaining = list(cards)
    overseers = GetMissionArea(effect).FindCards(
        trait="OVERSEER", card_type=Minion
    )
    if not overseers:
        return remaining

    overseer = overseers[0]

    if overseer.IsName("The Shadow King"):
        mental_resources = sum(
            card.printed_resource_internal.b
            for card in remaining
        )
        if mental_resources:
            mission.PlaceThreatOnSchemes([mission], 2 * mental_resources, effect)

    elif overseer.IsName("Sugar Man"):
        physical_resources = sum(
            card.printed_resource_internal.r
            for card in remaining
        )
        if physical_resources:
            overseer.HealthUnits([overseer], 3 * physical_resources, effect)

    elif overseer.IsName("Mikhail Rasputin"):
        energy_resources = sum(
            card.printed_resource_internal.y
            for card in remaining
        )
        for _ in range(energy_resources):
            allies = GetMissionAllies(effect)
            if not allies:
                break
            target = player.AskChooseFace(
                allies,
                effect,
                prompt="Choose an ally at the mission to take 1 damage",
            )
            if target:
                target.TakeDamage(overseer, 1, effect)

    elif overseer.IsName("Abyss"):
        wild_cards = [
            card for card in remaining
            if card.printed_resource_internal.g
        ]
        attached = Faces.MoveAllTo(
            wild_cards, overseer.GetInventoryDeck(), effect
        )
        if attached:
            Faces.FlipAllTo(attached, False, effect)
            attached_cards = {face.card for face in attached}
            remaining = [
                card for card in remaining
                if card.card not in attached_cards
            ]

    return remaining


def MakeMissionAttempt(player: 'Player', effect: 'Effect') -> None:
    mission = GetMissionScheme(effect)
    allies = GetMissionAllies(effect)
    if mission is None or not allies:
        return

    discarded = player.DiscardDeckTopCards(len(allies), effect)
    remaining = _resolve_overseer_discard_effects(
        discarded,
        player,
        mission,
        effect,
    )

    allies = GetMissionAllies(effect)
    sinister_is_present = any(
        overseer.IsName("Mister Sinister")
        for overseer in GetMissionMinions(effect)
        if overseer.HasTrait("OVERSEER")
    )
    used_resource_icons: Set[str] = set()
    assignments: List[Tuple['Ally', 'CardFace']] = []

    for ally in allies:
        legal_cards = remaining
        if sinister_is_present:
            legal_cards = [
                card for card in remaining
                if not (_resource_icons(card) & used_resource_icons)
            ]
        if not legal_cards:
            break
        assigned = player.AskChooseFace(
            legal_cards,
            effect,
            prompt=f"Assign a discarded card to {ally.name}",
            peek=True,
        )
        if not assigned:
            break
        remaining.remove(assigned)
        assignments.append((ally, assigned))
        used_resource_icons.update(_resource_icons(assigned))

    mission_allies = set(GetMissionAllies(effect))
    participating = [
        ally for ally, card in assignments
        if ally in mission_allies and _matching_resources(ally, card)
    ]

    damage = sum(ally.attack for ally in participating)
    for _ in range(damage):
        minions = GetMissionMinions(effect)
        if not minions:
            break
        non_overseers = [x for x in minions if not x.HasTrait("OVERSEER")]
        targets = non_overseers if non_overseers else minions
        target = player.AskChooseFace(
            targets,
            effect,
            prompt="Assign 1 mission-attempt damage",
        )
        if target:
            target.TakeDamage(effect.this, 1, effect)

    if mission.IsInPlay() and not GetMissionMinions(effect) and mission.threat == 0:
        mission.Defeated(effect.this, effect)

    if mission.IsInPlay():
        thwart = sum(ally.thwart for ally in participating)
        if thwart:
            from game.operate.store import Stores
            Stores.SetStr(MISSION_ATTEMPT_FLAG, "1", effect)
            effect.this.RemoveThreatFromSchemes([mission], thwart, effect)
            Stores.SetStr(MISSION_ATTEMPT_FLAG, "0", effect)

    # A successful mission has already flipped during the thwart resolution.
    mission = GetMissionScheme(effect)
    if mission is None:
        return

    Faces.PlaceCountersOn([mission], 1, "attempt", effect)
    for ally in GetMissionAllies(effect)[:]:
        ally.TakeDamage(effect.this, 1, effect)

    if mission.IsInPlay() and mission.GetCounters("attempt") >= 4:
        CompleteMission(mission, False, effect)


def _mission_cards_child_first(effect: 'Effect') -> List['CardFace']:
    def collect(face: 'CardFace') -> List['CardFace']:
        found: List['CardFace'] = []
        nested = (
            face.GetInventoryDeck().Get() +
            face.GetPlacedCardArea().Get()
        )
        for nested_face in nested:
            found.extend(collect(nested_face))
        found.append(face)
        return found

    found: List['CardFace'] = []
    for face in GetMissionArea(effect).Get()[:]:
        found.extend(collect(face))
    return found


def _return_player_cards_from_mission(effect: 'Effect') -> None:
    mission_allies = set(GetMissionAllies(effect))
    for face in _mission_cards_child_first(effect):
        owner = face.GetOwner()
        if Player.IsType(owner) and ClassCard.IsType(face):
            if face in mission_allies:
                face.TreatAsIfBlankInternal(-1, effect)
            Faces.ShuffleAllTo([face], owner.player_deck, effect)


def _remove_mission_area(effect: 'Effect') -> None:
    Faces.RemoveAllFromGame(_mission_cards_child_first(effect), effect)


def _resolve_finished_mission(
    mission_id: str,
    succeeded: bool,
    effect: 'Effect',
) -> None:
    players = Worlds.GetPlayers(effect)

    if mission_id == "45166a":
        if succeeded:
            for player in players:
                cards = effect.world.aside_deck.FindCards(name="Desperate Measures")
                if cards:
                    player.GainCard(cards[0], effect)
        else:
            effect.this.PlaceThreatOnSchemes("MainScheme", 2, effect)

    elif mission_id == "45167a":
        if succeeded:
            for player in players:
                card = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                    include_discard_pile=True,
                )
                if card:
                    player.GainCard(card, effect)
        else:
            for player in players:
                player.DealEncounterCards(1, effect)

    elif mission_id == "45168a":
        sea_walls = (
            Worlds.GetEncounterDeck(effect).FindCards(name="North American Sea Wall") +
            Worlds.GetEncounterDiscardPile(effect).FindCards(name="North American Sea Wall") +
            effect.world.area_schemes_side.FindCards(name="North American Sea Wall")
        )
        if succeeded:
            Faces.RemoveAllFromGame(sea_walls, effect)
            for player in players:
                player.ChooseAbilities(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Deal 3 damage to an enemy",
                        lambda targets:
                            effect.this.DealDamage(targets, 3, effect),
                    ).SetTarget(Enemy),
                )
        elif sea_walls:
            sea_walls[0].Reveal(Worlds.GetFirstPlayer(effect), effect)

    elif mission_id == "45169a":
        if succeeded:
            for player in players:
                allies = effect.world.aside_deck.FindCards(card_type=Ally)
                if not allies:
                    break
                ally = player.AskChooseFace(
                    allies,
                    effect,
                    prompt="Choose a campaign ally to add to your hand",
                    peek=True,
                )
                if ally:
                    player.GainCard(ally, effect)
        else:
            for player in players:
                if player.hand_cards.GetSize():
                    player.AskDiscardFace(player.hand_cards.Get(), effect)

    elif mission_id == "45170a":
        if succeeded:
            for player in players:
                ally = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                    include_discard_pile=True,
                    card_type=Ally,
                )
                if ally:
                    player.GainCard(ally, effect)
        else:
            Worlds.SetGameOver(False, effect)


def CompleteMission(
    mission: 'EncounterSideScheme',
    succeeded: bool,
    effect: 'Effect',
) -> None:
    mission_id = mission.paper.card_id
    team = GetMissionTeam(effect)

    if succeeded:
        _return_player_cards_from_mission(effect)
        if team:
            team.card.Flip(effect, call_reveal=False)
    elif team:
        Faces.RemoveAllFromGame([team], effect)

    _resolve_finished_mission(mission_id, succeeded, effect)
    _remove_mission_area(effect)
    if mission.IsInPlay():
        mission.card.Flip(effect, call_reveal=False)


def GetMissionFrontAbilities(*, protect_professor: bool=False) -> Sequence['Ability']:
    def mission_defeated(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        mission = effect.this.CastTo(EncounterSideScheme)
        CompleteMission(mission, True, effect)

    abilities: List['Ability'] = [
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            conditions=[
                lambda effect, message:
                    not Stores.HasKey(MISSION_ATTEMPT_FLAG, effect) or
                    Stores.GetStr(MISSION_ATTEMPT_FLAG, effect) != "1",
            ],
        ),
        AbilityFactory.CardCannotLeavePlayWhile(
            AbilityType.NonKeyword,
            "This",
            conditions=[
                lambda effect, message:
                    bool(GetMissionMinions(effect)),
            ],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            mission_defeated,
        ),
    ]

    if protect_professor:
        abilities.append(
            AbilityFactory.WhenCardWouldEnterPlay(
                AbilityType.NonKeyword,
                CardFinder(name="Professor X", card_type=Ally),
                lambda effect, message:
                    message.SetCannot(effect),
            )
        )

    return abilities


def GetOverseerAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            "This",
            conditions=[
                lambda effect, message:
                    any(
                        minion != effect.this and not minion.HasTrait("OVERSEER")
                        for minion in GetMissionMinions(effect)
                    ),
            ],
        ),
    ]
