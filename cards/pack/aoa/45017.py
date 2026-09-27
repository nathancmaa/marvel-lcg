from . import *

# Suit Up

def _CanAttachToAnAlly(upgrade: 'Upgrade') -> bool:
    from typing import get_args

    play_abilities = upgrade.ability.Find(func_name="Play")
    for ability in play_abilities:
        selector = next(
            (
                selector for selector in ability.selectors
                if selector and selector.target_text != "TeamUp"
            ),
            None,
        )
        if not selector:
            continue

        card_type = selector.selector_filter.finder.card_type
        if card_type == None and selector.target_text and \
            CardFinderHelper.IsFinderTarget(selector.target_text):
            card_type = CardFinderHelper.GetTargetType(selector.target_text)

        target_types = get_args(card_type) or (card_type,)
        if any(
            isinstance(target_type, type) and issubclass(Ally, target_type)
            for target_type in target_types
        ):
            return True
    return False


def _GetRequiredTargetCount(effect: 'Effect') -> int:
    legal_targets = effect.context.all_legal_targets
    available_types = int(bool(Filter.ByType(legal_targets, Ally))) + \
        int(bool(Filter.ByType(legal_targets, Upgrade)))

    # One of each type that exists; the search stays invalid when neither
    # an ally nor an attachable upgrade can be found.
    return max(1, available_types)

def GetAbilities() -> Sequence['Ability']:

    # def can_be_attached_to(upgrade: 'Upgrade', ally: 'Ally') -> bool:
    #     play_effect = upgrade.FindEffect(sub_type="Play")
    #     if play_effect:
    #         # TODO: Fix
    #         # if play_effect.ability.select_fn not in [Select.OnFieldAllies, Select.OnFieldFriendlyCharacters, Select.OnFieldCharacters, Select.YourAllies]:
    #         #     return False

    #         filter_fn_list = play_effect.ability.filter_fn_list[:]
    #         select_target = Filter(lambda effect: [ally], filter_fn_list)
    #         return ally in select_target.GetFilteredTargets(GameRule(upgrade))
    #     return False
    #     return True

    def suit_up(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()

        search_faces = initiator.player_deck.Get() + initiator.discard_pile.Get()
        all_allies = Filter.ByType(search_faces, Ally)
        all_upgrades = Filter.ByType(search_faces, Upgrade)
        selectable_faces = all_allies + all_upgrades

        Faces.LookAt(selectable_faces, initiator, effect)

        def can_attach_to_ally(effect: 'Effect', upgrade: 'CardFace') -> bool:
            if Upgrade.IsType(upgrade):
                return _CanAttachToAnAlly(upgrade)
            else:
                assert Ally.IsType(upgrade)
                return True

        initiator.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "",
                lambda targets:
                    initiator.GainCard(targets, effect)
            ).SetTarget(search_faces,
                finder=CardFinder(
                    card_type=Upgrade|Ally,
                    check_effect_fn=can_attach_to_ally
                ),
                select_rule="DifferentType",
                range=(_GetRequiredTargetCount, 2), by_search=True,
            ),
        )

    # def check_has_ally_and_upgrade(effect: 'Effect') -> Sequence['Ally']:
    #     initiator = effect.GetInitiator()
    #     deck_cards = initiator.player_deck.Get(True) + initiator.discard_pile.Get(True)
    #     upgrades = [x for x in deck_cards if Upgrade.IsType(x)]
    #     if upgrades == []:
    #         return []
    #     def has_upgrade(ally: Ally):
    #         for upgrade in upgrades:
    #             if can_be_attached_to(upgrade, ally):
    #                 return True
    #         return False
    #     return [x for x in deck_cards if Ally.IsType(x) and has_upgrade(x)]

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            suit_up,
        ).SetPlay().SetLabel()
    ]

