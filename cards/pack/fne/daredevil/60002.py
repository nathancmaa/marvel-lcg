from . import *

# Acute Tactility


def GetAbilities() -> Sequence['Ability']:

    def acute_tactility(effect: 'Effect', message: 'Message2') -> None:
        Unused(message)
        Faces.ReadyAll([effect.GetInitiator().GetIdentity()], effect)

    return [
        SenseCanAttachToEnemyOrScheme(),
        *SenseCompletionAbilities(acute_tactility),
    ]
