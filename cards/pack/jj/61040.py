from . import *

# Mitigated Threat

# The four icons the card names. Each is an IGNORE_KEY the engine already knows
# how to suppress -- the same switch a scheme uses when something tells it to
# ignore its own crisis icon.
MITIGATED_ICONS: Sequence['CardFace.IGNORE_KEY'] = (
    'Acceleration', 'Amplify', 'Crisis', 'Hazard',
)


def GetAbilities() -> Sequence['Ability']:

    def mitigate(effect: 'Effect', face: 'CardFace', diff: int) -> None:
        # Called with +1 when the upgrade attaches and -1 when it comes off, so
        # the icons come back on their own when the card is discarded.
        for keyword in MITIGATED_ICONS:
            face.SetIgnoreKeyword(diff, keyword, effect)

    def end_of_round(effect: 'Effect', message: 'Message.WhenRoundEnd') -> None:
        this = effect.this.CastTo(Upgrade)

        paid = [True]

        def ask(player: 'Player') -> None:
            if not player.AskSpendResources(Cost("1"), effect):
                paid[0] = False

        Players.ForEachPlayer(effect, ask)

        # One refusal is enough: it is the table that keeps this card alive.
        if not paid[0]:
            Faces.DiscardAll([this], effect)

    return [
        # "Attach to a card." The card it is for is a scheme -- the four icons
        # it takes away are a scheme's -- and with no target named it went on
        # the hero, where it did nothing.
        AbilityFactory.CanPlayThisUpgradeCard(Select.From("Scheme2")),
        *AbilityFactory.GiveKeywordToAttached(
            apply=mitigate,
        ),
        AbilityFactory.WhenRoundEnd(
            AbilityType.ForcedResponse,
            None,
            end_of_round,
        ),
    ]
