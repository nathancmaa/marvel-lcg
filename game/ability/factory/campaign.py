from . import *

class AbilityFactoryCampaign:

    @staticmethod
    def WhenCampaignSetup(operation: OperationType[Message.WhenCampaignSetup],
                        *,
                        conditions: ConditionsType[Message.WhenCampaignSetup]=[],
                        campaign_id: str|None=None,
                        ) -> 'Ability':
        from game.operate.worlds import Worlds
        return Ability(
            AbilityType.Campaign,
            Message.WhenCampaignSetup,
            [
                lambda effect, message:
                    Worlds.IsCampaign(effect) and (
                        campaign_id == None or
                        Worlds.IsCampaignSelected(effect, campaign_id)
                    ),
                *conditions
            ],
            operation
        )

    @staticmethod
    def WhenCampaignSetupExpertOnly(operation: OperationType[Message.WhenCampaignSetup],
                                    *,
                                    conditions: ConditionsType[Message.WhenCampaignSetup]=[],
                                    campaign_id: str|None=None,
                                    ) -> 'Ability':
        from game.operate.worlds import Worlds
        return AbilityFactoryCampaign.WhenCampaignSetup(
            operation,
            conditions=[
                lambda effect, message:
                    Worlds.IsExpert(effect),
                *conditions
            ],
            campaign_id=campaign_id,
        )

    @staticmethod
    def GetRemainingHitPoints(player: 'Player', effect: 'Effect') -> int|None:
        """The hit points logged for a player, or None when nothing is logged.

        A logged 0 is a real value -- the hero was defeated -- and must not
        read as "unset".
        """
        from game.operate.campaign_logs import CampaignLog
        player_id = player.player_id
        for key in [
            f"Player {player_id + 1} Remaining hit points",
            f"Remaining hit points P{player_id + 1}",
        ]:
            value = CampaignLog.GetStrInternal(key, effect).strip()
            if value == "":
                continue
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def CampaignSetPlayersHPToTheirRemainingHP(*, campaign_id: str|None=None) -> 'Ability':
        """Set each identity to the hit points logged after the last scenario.

        The campaign guides carry damage between scenarios only in an expert
        campaign; a standard campaign starts every scenario at full health.
        A hero logged at 0 was defeated. They cannot start the scenario
        defeated, so they start at 1 hit point, and the campaign's expert
        heal (offered next) is how they get back to full.
        """
        from game.operate.worlds import Worlds
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            for player in Worlds.GetPlayers(effect):
                value = AbilityFactoryCampaign.GetRemainingHitPoints(player, effect)
                if value is None:
                    continue
                identity = player.GetIdentity()
                identity.SetHealth(
                    max(1, min(value, identity.max_health)),
                    effect,
                )

        return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
            action,
            campaign_id=campaign_id,
        )

    @staticmethod
    def ExpertCampaignSetPlayersHPToTheirRemainingHP(*, campaign_id: str|None=None) -> 'Ability':
        # Alias kept for campaign modules that use the expert name.
        return AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id=campaign_id,
        )

    @staticmethod
    def PutCardIntoPlay(card_id: str, under_control: Literal["FirstPlayer"]|None=None, *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        from game.operate.worlds import Worlds
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            card = CardFactory.GenerateCard(
                card_id,
                Worlds.AsideDeck(effect),
                effect.world,
            )
            face = card.face
            face.PutIntoPlay("FirstPlayer", effect, under_control=under_control != None)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ShuffleCardIntoDeck(card_id: str, deck: Literal["EncounterDeck"], *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        from game.operate.faces import Faces
        from game.operate.worlds import Worlds
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            card = CardFactory.GenerateCard(
                card_id,
                Worlds.AsideDeck(effect),
                effect.world,
            )
            Faces.ShuffleAllTo([card.face], deck, effect)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ChooseCardAtRandomAndShuffleIntoEncounterDeck(card_ids: List[str], *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        from engine.lib import Random
        from game.operate.campaign_logs import CampaignLog
        from game.operate.faces import Faces
        from game.operate.worlds import Worlds
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            checked_ids = CampaignLog.GetList("Community Service: Victory for Scenarios #1-4", effect)
            card_id = Random.RandomChoice([x for x in card_ids if x not in checked_ids])
            card = CardFactory.GenerateCard(
                card_id,
                Worlds.AsideDeck(effect),
                effect.world,
            )
            Faces.ShuffleAllTo([card.face], "EncounterDeck", effect)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ExpertCampaignEachPlayerMayDealFacedownEncounterCardYpHealHP(size: int, *, campaign_id: str|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.ability.factory import AbilityFactory
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            this = effect.this

            for player in Worlds.GetPlayers(effect):
                def action(targets: Sequence['CardFace']):
                    player.DealEncounterCards(size, effect)
                    this.HealthUnits(targets, "All", effect)

                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        f"may deal themself {size} facedown encounter card from the encounter deck to set their hit point dial to their identity's printed hit point value",
                        action,
                    ).SetTarget([player.GetIdentity()], canbe_heal=True)
                )

        return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
            action,
            campaign_id=campaign_id,
        )

    @staticmethod
    def ExpertCampaignAddRandomObligationFromExpertCampaignToHealHP(obligations: Sequence[str], *, campaign_id: str|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.operate.campaign_logs import CampaignLog
        from game.card.factory import CardFactory
        from game.ability.factory import AbilityFactory
        from engine.lib import Random
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            this = effect.this

            rest_obligations: Dict[Player, List[str]] = {}

            for player in Worlds.GetPlayers(effect):
                player_id = player.player_id
                card_ids = CampaignLog.GetListByPlayer("Obligations", player_id, effect)
                rest_obligations[player] = [x for x in obligations if x not in card_ids]
                if card_ids:
                    CardFactory.GenerateCards(card_ids, player.player_deck, effect.world)
                    player.player_deck.Shuffle(effect)

            for player in Worlds.GetPlayers(effect):
                def action(targets: Sequence['CardFace']):
                    card_id = Random.RandomChoice(rest_obligations[player])
                    CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
                    this.HealthUnits(targets, "All", effect)
                    player.player_deck.Shuffle(effect)

                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Add 1 random obligation from expert campaign set to their deck to heal their identity to its full hit point value",
                        action,
                        condition=rest_obligations[player] != []
                    ).SetTarget([player.GetIdentity()], canbe_heal=True)
                )

        return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
            action,
            campaign_id=campaign_id,
        )
