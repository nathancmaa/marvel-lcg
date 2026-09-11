from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401

from cards.database import CardsDB
from engine.lib.image_creator import ImageCreator
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.card.face.card_face import CardFace
from game.element.damage_property import DamageProperty
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]

# Everything in the pack. 62001 has two faces; the rest are one card each.
LUKE_CAGE_CARDS = [
    "62001a,62001b",
    *[f"620{number:02d}" for number in range(2, 38)],
]

ENCOUNTER_CARDS = {"62028", "62029", "62030", "62031", "62032", "62033"}

# Cards printed again in this pack under a new number.
LUKE_CAGE_REPRINTS = {
    "62016": "21058",   # Innovation
    "62017": "01072",   # The Power of Leadership
    "62024": "61027",   # Unbreakable Bond, the other half of the pair
    "62025": "01088",   # Energy
    "62026": "01089",   # Genius
    "62027": "01090",   # Strength
}


def load_card(module: str):
    return importlib.import_module(module)


class LukeCageIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        ImageCreator.Initialize()

    def make_world(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(
                campaign_id="luke_cage_test",
                name="Luke Cage Test",
            ),
            players=[HeroDescriptor(
                version="",
                name="Luke Cage",
                hero=[],
                hero_deck=[],
                obligations=[],
                nemesis_set=[],
                player_deck=[],
            )],
        )
        world = World(scene, [SimpleNamespace(manager=manager)])
        world.rule.SetRule(scene.rules, False, 1)
        world.insert = CardFactory.GenerateCard(
            "rule_a,rule_b",
            world.area_insert,
            world,
            ui_render=False,
        ).face
        return world

    def test_every_card_in_the_pack_can_create_a_real_card_face(self):
        world = self.make_world()
        player = world.players[0]

        for card_id in LUKE_CAGE_CARDS:
            with self.subTest(card_id=card_id):
                if card_id == "62001a,62001b":
                    area = player.area_hero
                elif card_id in ENCOUNTER_CARDS:
                    area = world.GetScenario().encounter_deck
                else:
                    area = player.set_aside_deck

                card = CardFactory.GenerateCard(
                    card_id,
                    area,
                    world,
                    ui_render=False,
                )
                self.assertIsInstance(card.face, CardFace)

    def test_the_pack_is_complete(self):
        pack = json.loads(
            (ROOT / "data/cards.json").read_text(encoding="utf-8")
        )["luke_cage"]
        ids = {card["card_id"] for card in pack}

        expected = {"62001a", "62001b"}
        expected |= {f"620{number:02d}" for number in range(2, 38)}

        self.assertEqual(ids, expected)

    def test_reprints_link_to_their_first_printing(self):
        pack = json.loads(
            (ROOT / "data/cards.json").read_text(encoding="utf-8")
        )["luke_cage"]
        by_id = {card["card_id"]: card for card in pack}

        for card_id, first_printing in LUKE_CAGE_REPRINTS.items():
            with self.subTest(card_id=card_id):
                self.assertEqual(by_id[card_id].get("full_link"), first_printing)

    def test_the_starter_deck_is_the_published_precon(self):
        starter = json.loads(
            (ROOT / "deck/starter/luke_cage.json").read_text(encoding="utf-8")
        )

        self.assertEqual(len(starter["hero_deck"]), 15)
        self.assertEqual(len(starter["player_deck"]), 25)
        self.assertEqual(starter["hero"], ["62001a,62001b"])
        self.assertEqual(starter["obligations"], ["62028"])
        self.assertEqual(
            starter["nemesis_set"],
            ["62029", "62030", "62031", "62032", "62033"],
        )
        # Every card in it belongs to this pack, so the deck needs nothing
        # else installed to be playable.
        for card_id in starter["hero_deck"] + starter["player_deck"]:
            with self.subTest(card_id=card_id):
                self.assertTrue(card_id.startswith("62"))

    def test_the_pack_is_registered_as_a_set(self):
        sets = json.loads(
            (ROOT / "data/sets_info.json").read_text(encoding="utf-8")
        )
        entry = sets["62. Luke Cage"]
        self.assertEqual(entry["name"], "luke_cage")
        self.assertEqual(entry["heroes"], ["luke_cage"])
        self.assertEqual(entry["max_id"], "62037")

    def test_the_block_counter_is_registered(self):
        # Defensive Formation's uses. A counter name that is not on this list
        # places nothing.
        self.assertIn("block", CardFace.COUNTER_LIST)

    def test_luke_cage_can_hold_any_number_of_tough_cards(self):
        for module_name in ("cards.pack.luke_cage.luke_cage.62001a",
                            "cards.pack.luke_cage.luke_cage.62001b"):
            with self.subTest(module=module_name):
                module = load_card(module_name)
                with patch.object(
                    module.AbilityFactory, "ThisCanHaveAdditionalTough",
                ) as factory:
                    module.GetAbilities()
                factory.assert_called_once_with("Any")

    def test_shedding_a_tough_card_costs_him_one_damage_nothing_can_stop(self):
        module = load_card("cards.pack.luke_cage.luke_cage.62001a")
        operation = module.GetAbilities()[-1].operation

        effect = Mock()
        this = effect.this.CastTo.return_value
        operation(effect, Mock())

        this.TakeDamage.assert_called_once()
        property = this.TakeDamage.call_args.args[1]
        self.assertEqual(property.damage, 1)
        self.assertTrue(property.ignore_tough)
        self.assertTrue(property.unpreventable)

    def test_unpreventable_damage_refuses_to_be_reduced(self):
        from game.message import Message

        message = Mock(spec=Message.WhenUnitWouldTakeDamage)
        message.property = DamageProperty(3, unpreventable=True)
        reduce = Message.WhenUnitWouldTakeDamage.ReduceDamage
        prevent = Message.WhenUnitWouldTakeDamage.PreventDamage

        reduce(message, 1, Mock())
        self.assertEqual(message.property.damage, 3)
        self.assertEqual(prevent(message, "All", Mock()), 0)
        self.assertEqual(message.property.damage, 3)

        # Ordinary damage is still reducible, which is the whole point of the
        # flag being a flag.
        message.property = DamageProperty(3)
        reduce(message, 1, Mock())
        self.assertEqual(message.property.damage, 2)

    def test_internal_injury_hits_for_three_and_leaves_on_a_recover(self):
        module = load_card("cards.pack.luke_cage.luke_cage.62028")
        abilities = module.GetAbilities()
        self.assertEqual(len(abilities), 2)

        effect = Mock()
        identity = effect.this.GetOwnerPlayer.return_value.GetIdentity.return_value
        abilities[0].operation(effect, Mock())

        identity.TakeDamage.assert_called_once()
        property = identity.TakeDamage.call_args.args[1]
        self.assertEqual(property.damage, 3)
        self.assertTrue(property.ignore_tough)
        self.assertTrue(property.unpreventable)

    def test_misty_knight_is_only_bigger_while_she_is_tough(self):
        module = load_card("cards.pack.luke_cage.62013")
        with patch.object(module.AbilityFactory, "ThisGainKeyword") as factory:
            module.GetAbilities()

        self.assertEqual(factory.call_args.kwargs["attack"], 2)
        self.assertEqual(factory.call_args.kwargs["thwart"], 2)

        count = factory.call_args.args[0]
        effect = Mock()
        effect.this.CastTo.return_value.tough = 0
        self.assertFalse(count(effect, None))
        effect.this.CastTo.return_value.tough = 1
        self.assertTrue(count(effect, None))

    def test_jessica_jones_reads_your_identity_and_stops_at_four(self):
        module = load_card("cards.pack.luke_cage.luke_cage.62002")
        with patch.object(module.AbilityFactory, "ThisGainKeyword") as factory:
            module.GetAbilities()
        count = factory.call_args.args[0]

        effect = Mock()
        identity = effect.this.GetOwnerPlayer.return_value.GetIdentity.return_value
        with patch.object(module, "ToughOn", side_effect=lambda face: 7):
            self.assertEqual(count(effect, None), 4)
        with patch.object(module, "ToughOn", side_effect=lambda face: 2):
            self.assertEqual(count(effect, None), 2)
        self.assertIsNotNone(identity)

    def test_righteous_purpose_only_lifts_a_character_on_its_last_point(self):
        module = load_card("cards.pack.luke_cage.62019")
        with patch.object(module.CanHealth, "IsType", return_value=True):
            self.assertTrue(module.OnTheirLastHitPoint(SimpleNamespace(health=1)))
            self.assertFalse(module.OnTheirLastHitPoint(SimpleNamespace(health=2)))
            self.assertFalse(module.OnTheirLastHitPoint(SimpleNamespace(health=0)))

    def test_size_advantage_doubles_against_a_smaller_enemy(self):
        module = load_card("cards.pack.luke_cage.62034")
        operation = module.GetAbilities()[0].operation

        def damage_against(identity_health, enemy_health, giant):
            effect = Mock()
            enemy = SimpleNamespace(health=enemy_health)
            effect.targets = [enemy]
            identity = effect.GetInitiator.return_value.GetIdentity.return_value
            identity.health = identity_health
            identity.HasTrait.side_effect = lambda trait: giant
            with patch.object(module.CanHealth, "IsType", return_value=True):
                operation(effect, Mock())
            return effect.this.CastTo.return_value.DealDamage.call_args.args[1]

        self.assertEqual(damage_against(10, 4, False), 6)
        self.assertEqual(damage_against(4, 10, False), 3)
        # Equal hit points is not "more remaining hit points".
        self.assertEqual(damage_against(5, 5, False), 3)
        self.assertEqual(damage_against(1, 10, True), 6)


if __name__ == "__main__":
    unittest.main()
