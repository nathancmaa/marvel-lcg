from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        attachment = Worlds.DiscardEncounterCardsUntil(
            effect,
            card_type=Attachment,
            trait="VEHICLE",
        )
        if not attachment:
            return

        player = message.GetToPlayer()
        identity = player.GetIdentity()
        has_vehicle = bool(CardFinder(
            trait="VEHICLE",
            card_type=Attachment,
        ).Checks(identity.GetAttachedAttachments()))
        if has_vehicle:
            attachment.Reveal(player, effect)
            return

        # Name the discarded Vehicle, so the player knows what they would take.
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbilityWithCost(
                Cost("3", same_type=True),
                f"Spend 3 resources of the same type to attach {attachment.name} to your identity",
                lambda targets, resources: attachment.AttachTo2(identity, effect),
            ),
            AbilityFactory.ForChoiceAbility(
                f"Reveal {attachment.name}",
                lambda targets: attachment.Reveal(player, effect),
            ),
        )

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
