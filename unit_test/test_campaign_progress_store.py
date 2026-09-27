import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from engine import Engine  # noqa: F401 - preserve normal application import order
from game.game import Game
from game.game_run.campaign_progress import (
    CampaignProgressConflict,
    CampaignProgressStore,
)


class CampaignProgressStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = str(Path(self.temp_dir.name) / 'campaign.json')
        self.store = CampaignProgressStore(self.file_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def campaign(
        campaign_id='rise_of_red_skull',
        scenario_index=0,
        hero_id='spider_man',
        *,
        completed=False,
        campaign_log=None,
    ):
        return {
            'version': 1,
            'campaignId': campaign_id,
            'scenarioIndex': scenario_index,
            'heroId': hero_id,
            'campaignLog': campaign_log or {},
            'completed': completed,
            'updatedAt': '2026-08-11T10:00:00+00:00',
        }

    @staticmethod
    def active_run(
        campaign_id='rise_of_red_skull',
        scenario_id='crossbones',
        scenario_name='Crossbones',
        scenario_index=0,
    ):
        return {
            'version': 1,
            'campaignId': campaign_id,
            'scenarioId': scenario_id,
            'scenarioName': scenario_name,
            'scenarioIndex': scenario_index,
        }

    def start_request(self, *, campaign=None, active_run=None, replace=False):
        return {
            'campaign': campaign or self.campaign(),
            'activeRun': active_run or self.active_run(),
            'replace': replace,
        }

    def advance(self, **kwargs):
        # A game launched from the Campaign page carries the active run's id.
        record = self.store.Load()
        active_run = record['activeRun'] if record else None
        kwargs.setdefault('run_id', (active_run or {}).get('runId'))
        return self.store.AdvanceVerified(**kwargs)

    def test_progress_survives_a_new_store_instance(self):
        self.store.Start(self.start_request())

        restored = CampaignProgressStore(self.file_path).Load()

        self.assertIsNotNone(restored)
        self.assertEqual(restored['campaign']['campaignId'], 'rise_of_red_skull')
        self.assertEqual(restored['campaign']['heroId'], 'spider_man')
        self.assertEqual(restored['activeRun']['scenarioId'], 'crossbones')

    def test_new_campaign_requires_explicit_replacement(self):
        self.store.Start(self.start_request())
        replacement = self.start_request(
            campaign=self.campaign(
                campaign_id='sinister_motives',
                hero_id='daredevil',
            ),
            active_run=self.active_run(
                campaign_id='sinister_motives',
                scenario_id='sandman',
                scenario_name='Sandman',
            ),
        )

        with self.assertRaises(CampaignProgressConflict):
            self.store.Start(replacement)
        self.assertEqual(
            self.store.Load()['campaign']['campaignId'],
            'rise_of_red_skull',
        )

        replacement['replace'] = True
        self.store.Start(replacement)
        self.assertEqual(
            self.store.Load()['campaign']['campaignId'],
            'sinister_motives',
        )

    def test_local_storage_migration_never_overwrites_server_progress(self):
        first, migrated = self.store.Migrate({
            'campaign': self.campaign(),
            'activeRun': None,
        })
        second, migrated_again = self.store.Migrate({
            'campaign': self.campaign(
                campaign_id='sinister_motives',
                hero_id='daredevil',
            ),
            'activeRun': None,
        })

        self.assertTrue(migrated)
        self.assertFalse(migrated_again)
        self.assertEqual(first, second)
        self.assertEqual(second['campaign']['campaignId'], 'rise_of_red_skull')

    def test_defeat_does_not_advance_the_scenario(self):
        self.store.Start(self.start_request())

        result = self.advance(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={'Player 1 Remaining hit points': '0'},
            game_over=True,
            players_won=False,
            is_replay=False,
        )

        self.assertFalse(result['advanced'])
        self.assertEqual(result['reason'], 'not_victory')
        restored = self.store.Load()
        self.assertEqual(restored['campaign']['scenarioIndex'], 0)
        self.assertIsNotNone(restored['activeRun'])

    def test_victory_advances_exactly_once_and_merges_the_campaign_log(self):
        self.store.Start(self.start_request(
            campaign=self.campaign(campaign_log={'Unspent Units': '2'}),
        ))

        first = self.advance(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={
                'Unspent Units': '4',
                'Player 1 Remaining hit points': '7',
            },
            game_over=True,
            players_won=True,
            is_replay=False,
        )
        second = self.advance(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={'Unspent Units': '99'},
            game_over=True,
            players_won=True,
            is_replay=False,
        )

        self.assertTrue(first['advanced'])
        self.assertEqual(first['campaign']['scenarioIndex'], 1)
        self.assertEqual(first['campaign']['campaignLog']['Unspent Units'], '4')
        self.assertEqual(
            first['campaign']['campaignLog']['Player 1 Remaining hit points'],
            '7',
        )
        self.assertFalse(second['advanced'])
        self.assertEqual(second['reason'], 'already_recorded')
        self.assertEqual(second['campaign']['scenarioIndex'], 1)
        self.assertEqual(second['campaign']['campaignLog']['Unspent Units'], '4')

    def test_final_scenario_marks_the_campaign_complete(self):
        campaign = self.campaign(
            campaign_id='rise_of_red_skull',
            scenario_index=4,
        )
        active_run = self.active_run(
            scenario_id='red_skull',
            scenario_name='Red Skull',
            scenario_index=4,
        )
        self.store.Start(self.start_request(
            campaign=campaign,
            active_run=active_run,
        ))

        result = self.advance(
            campaign_id='rise_of_red_skull',
            scenario_name='Red Skull',
            campaign_log={},
            game_over=True,
            players_won=True,
            is_replay=False,
        )

        self.assertTrue(result['advanced'])
        self.assertTrue(result['campaign']['completed'])
        self.assertEqual(result['campaign']['scenarioIndex'], 4)

    def test_resumed_game_uses_the_authoritative_server_campaign_log(self):
        self.store.Start(self.start_request(
            campaign=self.campaign(campaign_log={'Unspent Units': '7'}),
        ))
        descriptor = SimpleNamespace(
            campaign_log={'Unspent Units': '1'},
            campaign_progress=self.start_request(
                campaign=self.campaign(campaign_log={'Unspent Units': '1'}),
            ),
        )
        game = Game.__new__(Game)
        scene = SimpleNamespace(metadata={})
        game.session = SimpleNamespace(world=None, NewGame=Mock(), scene=scene)
        game.controller_manager = SimpleNamespace(
            replay=SimpleNamespace(SetIsReplay=Mock()),
            OnNewGame=Mock(),
        )
        game.campaign_progress = self.store
        game.RemoveActiveSessionFile = Mock()

        game.NewGame(descriptor)

        self.assertEqual(descriptor.campaign_log, {'Unspent Units': '7'})
        game.session.NewGame.assert_called_once_with(descriptor)
        # The launched game is tagged as this run's, so only it can advance.
        self.assertEqual(
            CampaignProgressStore.GetSceneRunId(scene),
            self.store.Load()['activeRun']['runId'],
        )

    def test_a_game_not_launched_for_the_run_never_advances_it(self):
        # An Advanced Setup win of the same scenario (another hero, expert,
        # anything) has no run id, or an old one; the campaign stays put.
        self.store.Start(self.start_request(
            campaign=self.campaign(campaign_log={'Unspent Units': '2'}),
        ))
        for run_id in (None, '', 'someone-elses-run'):
            result = self.store.AdvanceVerified(
                campaign_id='rise_of_red_skull',
                scenario_name='Crossbones',
                campaign_log={'Unspent Units': '9'},
                game_over=True,
                players_won=True,
                is_replay=False,
                run_id=run_id,
            )
            self.assertFalse(result['advanced'])
            self.assertEqual(result['reason'], 'not_campaign_run')
        restored = self.store.Load()
        self.assertEqual(restored['campaign']['scenarioIndex'], 0)
        self.assertEqual(restored['campaign']['campaignLog'], {'Unspent Units': '2'})
        self.assertIsNotNone(restored['activeRun'])

    def test_each_launch_gets_its_own_run_id_and_tags_the_scene(self):
        scene = SimpleNamespace(metadata={})
        first = self.store.CommitPreparedStart(
            self.store.PrepareStart(self.start_request()), scene,
        )
        run_id = first['activeRun']['runId']
        self.assertTrue(run_id)
        self.assertEqual(CampaignProgressStore.GetSceneRunId(scene), run_id)

        again = self.store.PrepareStart(self.start_request())
        self.assertNotEqual(again['activeRun']['runId'], run_id)

    def test_a_run_recorded_before_run_ids_still_advances(self):
        self.store.Start(self.start_request())
        record = self.store.Load()
        record['activeRun'].pop('runId')
        self.store.CommitPreparedStart(record)

        result = self.store.AdvanceVerified(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={},
            game_over=True,
            players_won=True,
            is_replay=False,
        )
        self.assertTrue(result['advanced'])


if __name__ == '__main__':
    unittest.main()
