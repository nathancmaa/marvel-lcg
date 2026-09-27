from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        avatar = SwapAvatarWithRandomSetAside(effect)
        if not avatar:
            return
        player = message.GetToPlayer()
        bonus = 1 if Worlds.IsExpert(effect) else 0

        if avatar.IsName("Loki the Knave") or avatar.IsName("Loki the Miscreant"):
            avatar.DoSchemes(
                player,
                effect,
                operation=lambda scheme_message:
                    avatar.GainForThisActive(
                        effect,
                        scheme_message,
                        scheme=bonus,
                    ),
            )
        else:
            avatar.DoAttackYou(
                player,
                effect,
                operation=lambda attack_message:
                    avatar.GainForThisActive(
                        effect,
                        attack_message,
                        attack=bonus,
                    ),
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
