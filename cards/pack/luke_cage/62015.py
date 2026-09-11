from . import *

# Take a Stand


def GetAbilities() -> Sequence['Ability']:

    def take_a_stand(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> None:
        for ally in effect.GetInitiator().GetControlAllies():
            ally.GainUntilPhaseEnd(effect, attack=1, thwart=1)

    return [
        # A Response to the defence rather than an Interrupt to the attack: the
        # card fires after your hero has defended, so the allies are whichever
        # ones are still standing afterwards.
        AbilityFactory.AfterUnitDefendEnd(
            AbilityType.HeroResponse,
            "YourHero",
            take_a_stand,
        ).SetPlay().SetLabel(),
    ]
