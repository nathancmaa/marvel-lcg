"""Advanced Setup's campaign log rows follow the heroes picked.

The rows for players 2-4 were filtered once, when the log was drawn, and
picking a hero afterwards never showed them. The page's script is inline,
so these checks read it as text.
"""

from pathlib import Path
import re
import unittest


SCENE = Path(__file__).resolve().parents[1] / 'public' / 'scene.html'


def _function(html, name):
    start = html.index(f'function {name}(')
    depth = 0
    for index in range(html.index('{', start), len(html)):
        if html[index] == '{':
            depth += 1
        elif html[index] == '}':
            depth -= 1
            if depth == 0:
                return html[start:index + 1]
    raise AssertionError(name)


class AdvancedSetupCampaignLogTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = SCENE.read_text(encoding='utf-8')

    def test_rows_are_tagged_by_player_not_dropped(self):
        generate = _function(self.html, 'generateInputs')
        self.assertNotIn('length_of_heroes', generate)
        self.assertIn('row.dataset.playerNumber = playerNumber', generate)
        self.assertIn('updateCampaignPlayerRows()', generate)

    def test_picking_a_hero_refreshes_the_rows(self):
        self.assertIn('updateCampaignPlayerRows()', _function(self.html, 'SetHero'))

    def test_hidden_rows_are_not_sent_with_the_game(self):
        reader = _function(self.html, 'read_campaign_log')
        self.assertEqual(len(re.findall(r'inHiddenRow\(input\)', reader)), 2)

    def test_player_numbers_come_from_both_key_styles(self):
        helper = _function(self.html, 'campaignPlayerNumber')
        self.assertIn('/^Player (\\d+)/', helper)
        self.assertIn('/ P(\\d+)$/', helper)


if __name__ == '__main__':
    unittest.main()
