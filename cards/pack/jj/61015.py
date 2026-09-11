from . import *

# * Captain Marvel: Carol Danvers


def GetAbilities() -> Sequence['Ability']:

    def captain_marvel(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        this = effect.this.CastTo(Ally)
        initiator = effect.GetInitiator()

        discarded = initiator.DiscardDeckTopCards(4, effect)
        # The printed icon, and energy only: the finder counts a wild icon as
        # every colour unless it is told not to, which is what a card reading
        # "a printed [energy] resource" means.
        energy = CardFinder(has_printed_res="Y").Checks(discarded)

        if len(energy) >= 1:
            this.RemoveThreatFromSchemes(effect.targets, 2, effect)
        if len(energy) >= 2:
            Faces.GiveStatus(effect.targets2, "Confused", effect)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.Response,
            "This",
            captain_marvel,
        ).SetTarget(Scheme2)
        .SetTarget2(Enemy, canbe_confused=True),
    ]
