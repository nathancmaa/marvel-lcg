"""A restriction on which characters may remove threat does not bind a support."""
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.ability.condition import Condition
from game.ability.factory import AbilityFactory
from game.operate.worlds import Worlds


class ThreatRemovalByCharacterTests(unittest.TestCase):
    """Technovirus Purge: "Characters other than Cable cannot remove threat"."""

    def setUp(self):
        # Stands in for CardFinder(non_name="Cable"): who is named is the
        # finder's business, and mocks have no card names for it to read.
        anyone_but_cable = Mock()
        anyone_but_cable.Check = lambda face: face.name != 'Cable'
        self.ability = AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This", by_character=anyone_but_cable)
        self.scheme = Mock()
        self.effect = Mock()
        self.effect.this = self.scheme

    def restricted(self, by_face, characters):
        message = Mock()
        message.trigger = self.scheme
        message.would_thw_message = None
        message.by_face = by_face
        # The scheme is the one the threat leaves; that check needs a real
        # face, and is not what this tests.
        with (
            patch.object(Worlds, 'GetOnFieldCharacters', return_value=characters),
            patch.object(Condition, 'CheckWhichCard', return_value=True),
        ):
            return all(condition(self.effect, message) for condition in self.ability.conditions)

    def test_a_support_such_as_eva_may_remove_threat(self):
        eva = Mock()
        eva.name = 'E.V.A.'
        cable = Mock()
        cable.name = 'Cable'
        self.assertFalse(self.restricted(eva, characters=[cable]))

    def test_another_character_may_not(self):
        ally = Mock()
        ally.name = 'Fantomex'
        self.assertTrue(self.restricted(ally, characters=[ally]))

    def test_cable_himself_may(self):
        cable = Mock()
        cable.name = 'Cable'
        self.assertFalse(self.restricted(cable, characters=[cable]))


if __name__ == '__main__':
    unittest.main()
