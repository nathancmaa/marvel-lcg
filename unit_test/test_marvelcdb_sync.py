from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine.lib import Json
from engine.marvelcdb.deck_sync import MarvelCdbDeckSync


SPIDER_MAN_TEMPLATE = {
    'version': '0.6.0',
    'name': 'Spider-Man',
    'metadata': {'url': ''},
    'hero': ['01001a,01001b'],
    'hero_deck': [
        '01002',
        '01003', '01003',
        '01004', '01004',
        '01005', '01005', '01005',
        '01006',
        '01007', '01007',
        '01008', '01008',
        '01009', '01009',
    ],
    'set_aside': [],
    'obligations': ['01165'],
    'nemesis_set': ['01166', '01167', '01168', '01168', '01169'],
    'player_deck': ['old-card'],
}


def create_remote_deck(deck_id='1130039'):
    return {
        'id': int(deck_id),
        'name': 'Spider-Man unti Ultron',
        'date_update': '2026-02-23T16:58:54+00:00',
        'hero_code': '01001a',
        'hero_name': 'Spider-Man',
        'slots': {
            '01002': 1,
            '01003': 2,
            '01004': 2,
            '01005': 3,
            '01006': 1,
            '01007': 2,
            '01008': 2,
            '01009': 2,
            '01051': 1,
            '01052': 2,
            '01054': 2,
        },
    }


class TestMarvelCdbDeckSync(unittest.TestCase):

    def test_parse_deck_ids_normalizes_and_deduplicates(self):
        # Renamed from ParseDeckIds: it returns canonical references now, so
        # that a pasted decklist link keeps naming the decklist endpoint. A
        # bare ID has no kind to encode and still passes through unchanged.
        self.assertEqual(
            MarvelCdbDeckSync.ParseDeckRefs('1130039, 01130039,,1143133'),
            ['1130039', '1143133'],
        )

        with self.assertRaisesRegex(ValueError, 'Invalid MarvelCDB deck ID'):
            MarvelCdbDeckSync.ParseDeckRefs('1130039,deck-name')

    def test_convert_deck_keeps_identity_template_and_replaces_player_cards(self):
        converted = MarvelCdbDeckSync.ConvertDeck(
            create_remote_deck(),
            SPIDER_MAN_TEMPLATE,
        )

        self.assertEqual(converted['name'], 'Spider-Man')
        self.assertEqual(converted['deck_name'], 'Spider-Man unti Ultron')
        self.assertEqual(converted['hero_deck'], SPIDER_MAN_TEMPLATE['hero_deck'])
        self.assertEqual(
            converted['player_deck'],
            ['01051', '01052', '01052', '01054', '01054'],
        )
        self.assertEqual(converted['metadata']['marvelcdb_id'], '1130039')
        self.assertEqual(SPIDER_MAN_TEMPLATE['player_deck'], ['old-card'])

    def test_double_sided_hero_card_uses_unsuffixed_marvelcdb_code(self):
        template = {
            **SPIDER_MAN_TEMPLATE,
            'hero_deck': ['26002a,26002b'],
        }
        remote = create_remote_deck()
        remote['slots'] = {'26002': 1, '01051': 2}

        converted = MarvelCdbDeckSync.ConvertDeck(remote, template)

        self.assertEqual(converted['player_deck'], ['01051', '01051'])

    def test_shadowcat_forms_stay_set_aside_when_marvelcdb_lists_both_faces(self):
        template = {
            **SPIDER_MAN_TEMPLATE,
            'name': 'Shadowcat',
            'hero': ['32030a,32030b'],
            'set_aside': ['32031a,32031b'],
        }
        remote = create_remote_deck()
        remote['hero_code'] = '32030a'
        remote['slots'] = {
            '32031a': 1,
            '32031b': 1,
            '01051': 2,
        }

        converted = MarvelCdbDeckSync.ConvertDeck(remote, template)

        self.assertEqual(converted['set_aside'], ['32031a,32031b'])
        self.assertEqual(converted['player_deck'], ['01051', '01051'])

    def test_unsuffixed_double_sided_set_aside_code_is_also_excluded(self):
        template = {
            **SPIDER_MAN_TEMPLATE,
            'set_aside': ['26002a,26002b'],
        }
        remote = create_remote_deck()
        remote['slots'] = {'26002': 1, '01051': 2}

        converted = MarvelCdbDeckSync.ConvertDeck(remote, template)

        self.assertEqual(converted['player_deck'], ['01051', '01051'])

    def test_sync_writes_engine_deck_and_persists_schedule(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            state_file = os.path.join(user_folder, '.sync-state.json')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=state_file,
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            result = service.SyncDecks('1130039')

            self.assertTrue(result['ok'])
            self.assertEqual(result['synced'][0]['name'], 'Spider-Man unti Ultron')
            # Decks are named by the kind that was fetched; a bare ID resolves
            # to a decklist, so the bare `1130039.json` name is not written.
            output = MarvelCdbDeckSync._read_json(
                os.path.join(user_folder, 'decklist-1130039.json'),
            )
            self.assertFalse(
                os.path.exists(os.path.join(user_folder, '1130039.json')))
            self.assertEqual(output['deck_name'], 'Spider-Man unti Ultron')
            self.assertEqual(output['name'], 'Spider-Man')
            state = service.GetStatus()
            # Stored as the endpoint it resolved to rather than the bare ID
            # that was typed: the roster is read back from the deck on disk,
            # which records the kind it was actually fetched from. A bare ID
            # would make the next sync probe `deck/1130039` first and risk a
            # different deck that happens to share the number.
            self.assertEqual(
                state['deck_ids'],
                ['https://marvelcdb.com/decklist/view/1130039'],
            )
            self.assertEqual(
                [deck['id'] for deck in state['decks']], ['1130039'])
            self.assertTrue(state['last_sync'])

    def test_unsupported_hero_is_reported_without_writing_a_deck(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            state_file = os.path.join(user_folder, '.sync-state.json')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            remote = create_remote_deck()
            remote['hero_code'] = '99999a'
            remote['hero_name'] = 'Unimplemented Hero'
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=state_file,
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: remote,
            )

            result = service.SyncDecks('1130039')

            self.assertFalse(result['ok'])
            self.assertIn('has no starter deck', result['errors'][0]['error'])
            self.assertFalse(os.path.exists(os.path.join(user_folder, '1130039.json')))

    def test_daily_schedule_is_due_after_interval(self):
        service = MarvelCdbDeckSync(interval_seconds=24 * 60 * 60)
        recent = {
            'deck_ids': ['1130039'],
            'last_sync': datetime.now(timezone.utc).isoformat(),
        }
        old = {
            'deck_ids': ['1130039'],
            'last_sync': (
                datetime.now(timezone.utc) - timedelta(days=2)
            ).isoformat(),
        }

        remaining = service._seconds_until_sync(recent)
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 23 * 60 * 60)
        self.assertEqual(service._seconds_until_sync(old), 0)

    def test_periodic_worker_stops_cleanly_without_configured_decks(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = MarvelCdbDeckSync(
                user_deck_folder=temp_folder,
                state_file=os.path.join(temp_folder, '.sync-state.json'),
                starter_deck_folder=temp_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            service.Start()
            service.Stop()

            self.assertIsNotNone(service._thread)
            self.assertFalse(service._thread.is_alive())


class TestUnimplementedCardWarning(unittest.TestCase):
    """A synced deck can name cards this build has no data for.

    They sync and play until the missing card comes up, so the sync says so
    rather than leaving it to be discovered mid-game.
    """

    @staticmethod
    def _fake_db(known):
        return SimpleNamespace(
            papers={card_id: object() for card_id in known},
            TryFindCardPaper=lambda card_id: (
                object() if card_id in known else None),
        )

    def test_cards_missing_from_this_build_are_reported_once_each(self):
        import cards.database
        with patch.object(cards.database, 'CardsDB', self._fake_db({'01001', '01002'})):
            unknown = MarvelCdbDeckSync.UnimplementedCards(
                ['01001', '99991', '01002', '99991', '99992'])
        self.assertEqual(unknown, ['99991', '99992'])

    def test_nothing_is_reported_when_every_card_is_known(self):
        import cards.database
        with patch.object(cards.database, 'CardsDB', self._fake_db({'01001', '01002'})):
            self.assertEqual(
                MarvelCdbDeckSync.UnimplementedCards(['01001', '01002']), [])

    def test_an_unloaded_card_database_reports_nothing(self):
        """Otherwise the first sync after a restart flags every card in every
        deck, which is worse than staying quiet."""
        import cards.database
        with patch.object(cards.database, 'CardsDB', self._fake_db(set())):
            self.assertEqual(
                MarvelCdbDeckSync.UnimplementedCards(['01001', '99991']), [])

    def test_the_warning_reaches_the_sync_result(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=os.path.join(user_folder, '.sync-state.json'),
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            with patch.object(
                MarvelCdbDeckSync, 'UnimplementedCards',
                staticmethod(lambda card_ids: ['99991']),
            ):
                result = service.SyncDecks('1130039')

            self.assertTrue(result['ok'], result['errors'])
            self.assertEqual(len(result['warnings']), 1)
            warning = result['warnings'][0]
            self.assertEqual(warning['id'], '1130039')
            self.assertEqual(warning['cards'], ['99991'])
            # A deck with missing cards still syncs; it is playable up to a point.
            self.assertEqual(len(result['synced']), 1)

    def test_a_clean_sync_carries_an_empty_warning_list(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=os.path.join(user_folder, '.sync-state.json'),
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            with patch.object(
                MarvelCdbDeckSync, 'UnimplementedCards',
                staticmethod(lambda card_ids: []),
            ):
                result = service.SyncDecks('1130039')

            self.assertEqual(result['warnings'], [])


class TheRosterIsTheDecksOnDisk(unittest.TestCase):
    """Syncing one deck must not be a way to lose the others.

    Typing a single ID into the sync box used to replace the stored list
    outright. The decks stayed on disk and stayed playable, so nothing looked
    broken -- but the table showed one row and the nightly refresh quietly
    stopped covering everything else.
    """

    def service(self, temp_folder: str, deck_ids=('1130039',)):
        starter_folder = os.path.join(temp_folder, 'starter')
        user_folder = os.path.join(temp_folder, 'user-decks')
        os.makedirs(starter_folder, exist_ok=True)
        Json.Save(
            SPIDER_MAN_TEMPLATE,
            os.path.join(starter_folder, 'spider_man.json'),
        )
        return MarvelCdbDeckSync(
            user_deck_folder=user_folder,
            state_file=os.path.join(user_folder, '.sync-state.json'),
            starter_deck_folder=starter_folder,
            fetch_deck=lambda deck_id: create_remote_deck(deck_id),
        )

    def test_syncing_one_deck_adds_it_and_keeps_the_rest(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)

            service.SyncDecks('1130039')
            service.SyncDecks('1143133')

            ids = sorted(deck['id'] for deck in service.GetStatus()['decks'])
            self.assertEqual(ids, ['1130039', '1143133'])
            self.assertEqual(len(service.GetStatus()['deck_ids']), 2)

    def test_the_roster_survives_a_state_file_that_forgot_everything(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)
            service.SyncDecks('1130039')
            service.SyncDecks('1143133')

            # The shape of the bug: the stored list, overwritten with one entry.
            state = service.GetStatus()
            state['deck_ids'] = ['1143133']
            state.pop('decks', None)
            service._save_state(state)

            # Read back from the decks themselves, so nothing was orphaned.
            recovered = service.GetStatus()
            self.assertEqual(
                sorted(deck['id'] for deck in recovered['decks']),
                ['1130039', '1143133'],
            )
            self.assertEqual(len(recovered['deck_ids']), 2)

    def test_an_empty_box_refreshes_everything_already_there(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)
            service.SyncDecks('1130039')
            service.SyncDecks('1143133')

            result = service.SyncDecks('')

            self.assertEqual(
                sorted(deck['id'] for deck in result['synced']),
                ['1130039', '1143133'],
            )

    def test_an_empty_box_with_nothing_to_refresh_still_asks_for_one(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)
            with self.assertRaises(ValueError):
                service.SyncDecks('')

    def test_one_deck_is_listed_once_however_it_was_named(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)

            service.SyncDecks('1130039')
            service.SyncDecks('https://marvelcdb.com/decklist/view/1130039')

            status = service.GetStatus()
            self.assertEqual(len(status['decks']), 1)
            # And the reference kept is the one that names the endpoint, so the
            # next sync does not have to guess between deck/ and decklist/.
            self.assertEqual(
                status['deck_ids'],
                ['https://marvelcdb.com/decklist/view/1130039'],
            )

    def test_removing_a_deck_is_a_separate_deliberate_act(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)
            service.SyncDecks('1130039')
            service.SyncDecks('1143133')
            user_folder = os.path.join(temp_folder, 'user-decks')

            result = service.ForgetDecks('1130039')

            self.assertTrue(result['ok'])
            self.assertEqual(
                [deck['id'] for deck in result['removed']], ['1130039'])
            self.assertFalse(
                os.path.exists(
                    os.path.join(user_folder, 'decklist-1130039.json')))
            status = service.GetStatus()
            self.assertEqual(
                [deck['id'] for deck in status['decks']], ['1143133'])
            self.assertEqual(len(status['deck_ids']), 1)

    def test_a_deck_that_is_not_from_marvelcdb_is_left_out_of_the_roster(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = self.service(temp_folder)
            service.SyncDecks('1130039')

            # A hand-made deck sitting in the same folder.
            user_folder = os.path.join(temp_folder, 'user-decks')
            Json.Save(
                {'name': 'Spider-Man', 'deck_name': 'Made by hand'},
                os.path.join(user_folder, 'by-hand.json'),
            )

            status = service.GetStatus()
            self.assertEqual(
                [deck['id'] for deck in status['decks']], ['1130039'])


if __name__ == '__main__':
    unittest.main()
