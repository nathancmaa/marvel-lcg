from . import *

# Teleport Drop

def GetAbilities() -> Sequence['Ability']:

    def teleport_drop(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        this.DealDamage(effect.targets, 8, effect)
        Faces.GiveStatus(effect.targets, "Stunned", effect)

    def get_bamf_cost(effect: 'Effect') -> Sequence['CardFace']:
        # Asked twice, and the first time there is no target yet.
        #
        # Deciding whether this card can be played at all happens before an
        # enemy is chosen, so reading effect.targets[0] there found nothing and
        # reported no Bamf to discard -- which made a (1, 1) discard cost
        # impossible to pay and the card unplayable however many Bamfs were on
        # the table. Falling back to the enemies it could legally be aimed at
        # answers the real question at that point: is there a Bamf anywhere
        # this card could take one from. By payment time effect.targets holds
        # the chosen enemy and this narrows to that enemy's Bamf.
        enemies = effect.targets or effect.context.all_legal_targets
        bamfs: List['CardFace'] = []
        for enemy in enemies:
            bamf = enemy.GetInventoryDeck().FindCard(name="Bamf!")
            if bamf and bamf not in bamfs:
                bamfs.append(bamf)
        return bamfs

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            teleport_drop
        ).SetPlay().SetLabel('attack')
        .SetCostFunc(CostFunc.Discard(
            Select.From(get_bamf_cost, range=(1, 1)),
        ))
        .SetTarget(Enemy, with_attach=CardFinder(name="Bamf!")),
    ]
