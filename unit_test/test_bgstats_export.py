"""The BG Stats play file: every decided game, in the app's own shape."""
from datetime import datetime, timezone
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.statistics.bgstats_export import BuildBgStatsFile


def game(**overrides):
    row = {
        'id': 7,
        'finished_at': '2026-09-11T22:15:30+00:00',
        'hero_name': 'Black Panther',
        'villain_name': 'Rhino',
        'expert': 0,
        'heroic': 0,
        'result': 'win',
        'rounds': 6,
        'playtime_seconds': 1830,
        'deck_name': "Shuri's Fury",
        'notes': '',
    }
    row.update(overrides)
    return row


NOW = datetime(2026, 9, 12, 8, 0, 0, tzinfo=timezone.utc)


class ThePlayFileHoldsEveryGame(unittest.TestCase):

    def test_one_game_one_player_and_the_plays_that_refer_to_them(self):
        content = BuildBgStatsFile([game(), game(id=8, result='loss', expert=1)], 'Nathan', 'Home', NOW)

        self.assertEqual([g['id'] for g in content['games']], [1])
        self.assertEqual([p['id'] for p in content['players']], [1])
        self.assertEqual([l['name'] for l in content['locations']], ['Home'])
        self.assertEqual(content['userInfo'], {'meRefId': 1})
        self.assertEqual(len(content['plays']), 2)
        for play in content['plays']:
            self.assertEqual(play['gameRefId'], 1)
            self.assertEqual(play['locationRefId'], 1)
            self.assertEqual(play['playerScores'][0]['playerRefId'], 1)

    def test_a_play_carries_the_result_the_hero_and_the_scenario(self):
        content = BuildBgStatsFile([game()], 'Nathan', '', NOW)
        play = content['plays'][0]
        score = play['playerScores'][0]

        self.assertTrue(score['winner'])
        self.assertEqual(score['role'], 'Black Panther')
        self.assertEqual(play['board'], 'Rhino')
        self.assertEqual(play['playDate'], '2026-09-11 22:15:30')
        self.assertEqual(play['durationMin'], 31)
        self.assertEqual(play['rounds'], 6)
        self.assertEqual(play['comments'], "Standard · 6 rounds · Shuri's Fury")
        self.assertNotIn('locationRefId', play)
        self.assertEqual(content['locations'], [])

    def test_a_loss_is_not_a_win_and_expert_is_said(self):
        play = BuildBgStatsFile([game(result='loss', expert=1, heroic=2)], 'Nathan', '', NOW)['plays'][0]
        self.assertFalse(play['playerScores'][0]['winner'])
        self.assertTrue(play['comments'].startswith('Heroic 2 · Expert'))

    def test_the_same_game_gets_the_same_uuid_every_time(self):
        # BG Stats recognises objects by UUID across imports, so a second
        # file must name the same play, player and game as the first.
        first = BuildBgStatsFile([game()], 'Nathan', 'Home', NOW)
        second = BuildBgStatsFile([game()], 'Nathan', 'Home', datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(first['plays'][0]['uuid'], second['plays'][0]['uuid'])
        self.assertEqual(first['games'][0]['uuid'], second['games'][0]['uuid'])
        self.assertEqual(first['players'][0]['uuid'], second['players'][0]['uuid'])
        self.assertEqual(first['locations'][0]['uuid'], second['locations'][0]['uuid'])
        self.assertNotEqual(first['plays'][0]['uuid'],
                            BuildBgStatsFile([game(id=8)], 'Nathan', 'Home', NOW)['plays'][0]['uuid'])

    def test_a_local_time_is_written_as_utc(self):
        play = BuildBgStatsFile([game(finished_at='2026-09-11T18:15:30-04:00')], 'Nathan', '', NOW)['plays'][0]
        self.assertEqual(play['playDate'], '2026-09-11 22:15:30')

    def test_an_empty_name_is_still_a_player(self):
        self.assertEqual(BuildBgStatsFile([game()], '  ', '', NOW)['players'][0]['name'], 'Me')


if __name__ == '__main__':
    unittest.main()
