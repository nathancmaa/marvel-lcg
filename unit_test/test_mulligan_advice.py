"""The deck author's opening-hand advice, from description to descriptor.

Both halves of this are worth pinning. The extractor half is judgement about
free-form prose and will drift as the regexes are tuned. The delivery half
already broke once, silently: the metadata sits on the scene's HeroDescriptor,
not on the runtime Player, so reading it off the player produced an empty list
and a panel that simply showed nothing -- indistinguishable from a deck whose
author said nothing about the mulligan.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from engine import Engine  # noqa: F401
from engine.lib.version import Ver
from engine.marvelcdb.mulligan_notes import (
    AttachMulliganAdvice,
    ExtractMulliganAdvice,
)
from cards.database import CardsDB
from game.render.mulligan_suggest import SUGGESTION_COUNT, SuggestMulliganCards
from game.render.to_descriptor import ToDescriptor
from game.scene.loader import SceneLoader
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class TestExtractMulliganAdvice(unittest.TestCase):

    def test_it_takes_the_cards_named_around_the_advice(self):
        description = (
            'This deck wants to set up fast. '
            '[Meditation](/card/26036) makes set up a breeze when you '
            'mulligan hard for it and [Avengers Mansion](/card/01091)/'
            '[Helicarrier](/card/01092).'
        )
        cards, note = ExtractMulliganAdvice(description)
        self.assertEqual(cards, ['26036', '01091', '01092'])
        self.assertIn('mulligan hard for it', note)

    def test_a_card_far_from_the_advice_is_not_dragged_in(self):
        description = (
            'Mulligan for [Meditation](/card/26036). ' + 'filler. ' * 90
            + 'Later on you will want [Enhanced Reflexes](/card/01064).'
        )
        cards, _ = ExtractMulliganAdvice(description)
        self.assertEqual(cards, ['26036'])

    def test_advice_with_no_cards_named_yields_nothing(self):
        # A note with no cards to point at is advice without a subject, and
        # showing it would be worse than showing nothing.
        cards, note = ExtractMulliganAdvice(
            'Mulligan aggressively; you know what you are looking for.')
        self.assertEqual(cards, [])
        self.assertEqual(note, '')

    def test_a_description_that_never_mentions_it_yields_nothing(self):
        # A little over half of real decks land here. That is the ordinary
        # answer, not a failure.
        cards, note = ExtractMulliganAdvice(
            'A [Meditation](/card/26036) deck for beginners.')
        self.assertEqual(cards, [])
        self.assertEqual(note, '')

    def test_nothing_is_attached_when_there_is_nothing_to_say(self):
        metadata = {'marvelcdb_id': '1'}
        AttachMulliganAdvice(metadata, 'No advice here.')
        self.assertEqual(metadata, {'marvelcdb_id': '1'})

    def test_what_is_attached_is_small_enough_to_travel_in_a_url(self):
        # The deck this rides on reaches the table as a query string, so the
        # budget is a few hundred bytes and not a few thousand.
        metadata: dict = {}
        AttachMulliganAdvice(metadata, 'Mulligan for ' + ''.join(
            f'[Card {index}](/card/0000{index}) ' for index in range(9)))
        self.assertLessEqual(len(json.dumps(metadata)), 512)
        self.assertLessEqual(len(metadata['mulligan_cards'].split(',')), 8)


class TestSuggestMulliganCards(unittest.TestCase):
    """The fallback for the ~3 in 4 decks whose author wrote nothing.

    These pin the behaviour the measurement is confident about -- the two
    strong negatives held their sign across all twenty half-splits -- rather
    than exact orderings, which 23 decks cannot justify freezing.
    """

    def starter(self, name: str = 'spider_man'):
        deck = json.loads(
            (ROOT / f'deck/starter/{name}.json').read_text(encoding='utf-8'))
        return deck.get('player_deck', []), deck.get('hero_deck', [])

    def test_it_suggests_a_hands_worth_from_a_real_deck(self):
        player_deck, hero_deck = self.starter()
        picks = SuggestMulliganCards(player_deck, hero_deck)
        self.assertEqual(len(picks), SUGGESTION_COUNT)
        self.assertEqual(len(set(picks)), len(picks))
        for card_id in picks:
            self.assertIn(card_id, set(player_deck) | set(hero_deck))

    def test_it_never_suggests_a_plain_resource(self):
        # The strongest signal in the data, at 0.17: across 23 decks authors
        # essentially never say to keep one, and it never crossed 1.0 in any
        # half-split.
        player_deck, hero_deck = self.starter()
        for card_id in SuggestMulliganCards(player_deck, hero_deck):
            paper = CardsDB.TryFindCardPaper(card_id)
            self.assertNotEqual(paper.type, 'Resource', paper.name)

    def test_the_same_deck_always_suggests_the_same_cards(self):
        # The panel redraws on every world update, so an unstable order would
        # reshuffle the chips under the player mid-mulligan.
        player_deck, hero_deck = self.starter()
        first = SuggestMulliganCards(player_deck, hero_deck)
        second = SuggestMulliganCards(list(reversed(player_deck)), hero_deck)
        self.assertEqual(first, second)

    def test_an_empty_deck_suggests_nothing(self):
        self.assertEqual(SuggestMulliganCards([], []), [])


class TestAdviceReachesThePlayerDescriptor(unittest.TestCase):

    def build_player_descriptor(self, metadata: dict):
        scenario = json.loads(
            (ROOT / 'data/scenarios/rhino.json').read_text(encoding='utf-8'))
        hero = json.loads(
            (ROOT / 'deck/starter/spider_man.json').read_text(encoding='utf-8'))
        hero['metadata'] = metadata

        scene = SceneLoader.NewFromJson(
            json.dumps(scenario),
            None,
            [json.dumps(hero)],
            1,
            ['v18_all', 'disable_setup_draw_cards', 'disable_resolve_mulligans'],
            {},
        )
        manager = Mock()
        manager.skip.is_skipping = True
        manager.undo.GetFastUndoHandle.return_value = None
        world = World(scene, [Mock(manager=manager)])
        return ToDescriptor.Player(world.players[0])

    def test_the_advice_on_the_deck_arrives_on_the_descriptor(self):
        descriptor = self.build_player_descriptor({
            'mulligan_cards': '26036,01091',
            'mulligan_note': 'Mulligan hard for Meditation.',
        })
        self.assertEqual(descriptor.mulligan_cards, ['26036', '01091'])
        self.assertEqual(descriptor.mulligan_note, 'Mulligan hard for Meditation.')

    def test_author_advice_is_labelled_as_the_authors(self):
        descriptor = self.build_player_descriptor({
            'mulligan_cards': '26036',
            'mulligan_note': 'Mulligan hard for Meditation.',
        })
        self.assertEqual(descriptor.mulligan_source, 'author')

    def test_a_deck_with_no_advice_falls_back_and_says_so(self):
        # Not empty any more: a deck nobody wrote about is ranked from its own
        # composition, and the source says which claim is being made so the
        # panel never presents our ranking as somebody's advice.
        descriptor = self.build_player_descriptor({})
        self.assertEqual(descriptor.mulligan_source, 'deck')
        self.assertEqual(len(descriptor.mulligan_cards), SUGGESTION_COUNT)
        self.assertEqual(descriptor.mulligan_note, '')


if __name__ == '__main__':
    unittest.main()
