"""The solo Campaign page's log editor and the server agree on the keys.

The editor is TypeScript and the server validates every key it saves
against CampaignLog.GetKnownKeys, so a field the engine does not know would
fail to save at the table. This reads the field list from the source.
"""

import asyncio
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest

from engine import Engine  # noqa: F401 - project import order
from engine.device.web.server.server_campaign_progress import GameServerCampaignProgress
from game.game_run.campaign_progress import CAMPAIGN_SCENARIOS, CampaignProgressStore
from game.operate.campaign_logs import CampaignLog


ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / 'public' / 'js' / 'campaign_log_editor.ts'
PAGE = ROOT / 'public' / 'campaign.html'


def _editor_keys():
    source = EDITOR.read_text(encoding='utf-8')
    keys = set(re.findall(r"key: '([^']+)'", source))
    for template in re.findall(r"key: `([^`]+)`", source):
        for scenario in range(1, 6):
            keys.add(template.replace('${scenario}', str(scenario)))
    return source, keys


class CampaignLogEditorTests(unittest.TestCase):

    def test_every_editor_field_is_a_known_campaign_log_key(self):
        _, keys = _editor_keys()
        self.assertGreater(len(keys), 40)
        unknown = sorted(keys - CampaignLog.GetKnownKeys())
        self.assertEqual(unknown, [])

    def test_every_campaign_has_editor_fields(self):
        source, _ = _editor_keys()
        for campaign_id in CAMPAIGN_SCENARIOS:
            self.assertRegex(source, rf"\n    {campaign_id}: \[")

    def test_the_evidence_seed_is_never_offered(self):
        _, keys = _editor_keys()
        self.assertNotIn('Evidence Seed', keys)

    def test_page_has_the_editor_and_its_save_route(self):
        page = PAGE.read_text(encoding='utf-8')
        self.assertIn('id="campaign-log-section"', page)
        self.assertIn('id="save-campaign-log"', page)
        state = (ROOT / 'public' / 'js' / 'campaign_state.ts').read_text(encoding='utf-8')
        self.assertIn("'/campaign_progress/log'", state)


class FakeRequest:

    def __init__(self, body, *, raise_on_json=False):
        self._body = body
        self._raise_on_json = raise_on_json

    async def json(self):
        if self._raise_on_json:
            raise ValueError('not json')
        return self._body


class CampaignLogRouteTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = CampaignProgressStore(str(Path(self.folder.name) / 'campaign.json'))
        self.server = object.__new__(GameServerCampaignProgress)
        game = SimpleNamespace(campaign_progress=self.store)
        self.server.device_manager = SimpleNamespace(
            controllers=[SimpleNamespace(game=game)])

    def tearDown(self):
        self.folder.cleanup()

    def call(self, body, **kwargs):
        response = asyncio.run(self.server.update_campaign_log(FakeRequest(body, **kwargs)))
        return response.status, json.loads(response.text)

    def start(self):
        self.store.Start({
            'campaign': {
                'version': 1, 'campaignId': 'mutant_genesis', 'scenarioIndex': 1,
                'heroId': 'cyclops', 'campaignLog': {}, 'completed': False,
            },
            'activeRun': {
                'version': 1, 'campaignId': 'mutant_genesis',
                'scenarioId': 'project_wideawake', 'scenarioName': 'Project Wideawake',
                'scenarioIndex': 1,
            },
            'replace': True,
        })
        return self.store.Load()['campaign']['updatedAt']

    def test_saves_a_known_entry(self):
        updated_at = self.start()
        status, payload = self.call({
            'campaignLog': {'Player 1 Role': 'Defender'},
            'updatedAt': updated_at,
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload['campaign']['campaignLog'], {'Player 1 Role': 'Defender'})
        self.assertEqual(
            self.store.Load()['campaign']['campaignLog'], {'Player 1 Role': 'Defender'})

    def test_bad_bodies_are_400_and_change_nothing(self):
        self.start()
        for body in ([], 'text', {'campaignLog': {'Nope': 'x'}}, {'campaignLog': {'Player 1 Role': 3}}):
            with self.subTest(body=body):
                status, payload = self.call(body)
                self.assertEqual(status, 400)
                self.assertIn('error', payload)
        status, _ = self.call(None, raise_on_json=True)
        self.assertEqual(status, 400)
        self.assertEqual(self.store.Load()['campaign']['campaignLog'], {})

    def test_a_stale_page_is_a_409(self):
        self.start()
        status, payload = self.call({
            'campaignLog': {'Player 1 Role': 'Defender'},
            'updatedAt': 'long ago',
        })
        self.assertEqual(status, 409)
        self.assertIn('error', payload)


if __name__ == '__main__':
    unittest.main()
