from . import *


def GetAbilities() -> Sequence['Ability']:
    def setup(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)

        avatar = GetRandomSetAsideAvatar(effect)
        if avatar:
            avatar.PutIntoPlay(first_player, effect)
            avatar.SetActive(effect)

        for environment in Worlds.GetSetAsideAreaCards(
            effect,
            CardFinder(trait="SYNERGY", card_type=Environment),
        ):
            environment.PutIntoPlay(first_player, effect)

        if Worlds.IsExpert(effect) and avatar:
            SetupCards.AttachTo(
                effect,
                attach_to=avatar,
                name="Intense Focus",
                card_type=Attachment,
            )

        worlds = Worlds.MainSchemesDeck(effect).FindCard(
            name="Worlds Collide",
            card_type=MainScheme,
        )
        if worlds:
            worlds.Reveal(first_player, effect)

    return [
        AbilityFactory.WhenCardSetup("This", setup),
    ]
