"""An action on a card attached to an identity is that identity's player's."""
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.ability.ability_type import AbilityType
from game.ability.factory import AbilityFactory
from game.card.face.card_type import Identity
from game.player import Player


class AttachedIdentityActionTests(unittest.TestCase):

    def setUp(self):
        self.ability = AbilityFactory.WhenInYourPlayTurn(AbilityType.AlterEgoAction, lambda effect, message: None)
        self.x23 = Mock(spec=Player)
        self.cable = Mock(spec=Player)

    def offered_to(self, player, attached_to_player):
        effect = Mock()
        effect.initiator = player
        if attached_to_player is None:
            effect.this = Mock(spec=[])  # nothing attached, no bind_face
        else:
            effect.this.bind_face.GetControlBy.return_value = attached_to_player
        message = Mock()
        message.to_player = player
        with patch.object(Identity, 'IsType', return_value=attached_to_player is not None):
            return self.ability.conditions[0](effect, message)

    def test_frozen_on_x23_is_x23s_to_discard_and_not_cables(self):
        self.assertTrue(self.offered_to(self.x23, attached_to_player=self.x23))
        self.assertFalse(self.offered_to(self.cable, attached_to_player=self.x23))

    def test_a_card_attached_to_nobody_is_offered_as_before(self):
        self.assertTrue(self.offered_to(self.cable, attached_to_player=None))

    def test_it_is_still_only_offered_on_that_players_turn(self):
        effect = Mock()
        effect.initiator = self.x23
        effect.this = Mock(spec=[])
        message = Mock()
        message.to_player = self.cable
        self.assertFalse(self.ability.conditions[0](effect, message))


if __name__ == '__main__':
    unittest.main()
