import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from cards.database import CardsDB
from cards.paper import Paper
from engine.device.web.server.server_get import GameServerGet


class TestDeckViewerCardMetadata(unittest.IsolatedAsyncioTestCase):

    async def test_card_paper_is_returned_as_json(self) -> None:
        paper = Paper(
            card_id='16012',
            pic_id='',
            type='Ally',
            is_unique=True,
            name='Starhawk',
            desc={'Cost': '2', 'Class': 'Protection'},
            traits=['AERIAL', 'GUARDIAN'],
            pack='gmw',
        )
        request = SimpleNamespace(
            rel_url=SimpleNamespace(query_string='16012'),
        )

        with patch.object(CardsDB, 'TryFindCardPaper', return_value=paper):
            response = await GameServerGet.get_card_json(
                object.__new__(GameServerGet),
                request,
            )

        self.assertEqual(response.content_type, 'application/json')
        payload = json.loads(response.text)
        self.assertEqual(payload['card_id'], '16012')
        self.assertEqual(payload['name'], 'Starhawk')
        self.assertEqual(payload['pack'], 'gmw')
        self.assertEqual(payload['desc']['Class'], 'Protection')

    async def test_a_card_this_build_lacks_is_a_404_not_a_crash(self) -> None:
        """A synced deck can name cards from a pack that is not implemented.

        The lookup used to assert, so every such card became a 500 and a
        traceback in the server log while the viewer was simply listing a deck.
        The client already substitutes a placeholder on a failed fetch.
        """
        request = SimpleNamespace(
            rel_url=SimpleNamespace(query_string='61015'),
        )

        with patch.object(CardsDB, 'TryFindCardPaper', return_value=None):
            response = await GameServerGet.get_card_json(
                object.__new__(GameServerGet),
                request,
            )

        self.assertEqual(response.status, 404)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')


if __name__ == '__main__':
    unittest.main()
