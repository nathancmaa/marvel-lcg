"""Every card script builds its abilities.

A card's abilities are built the first time a card of it is generated, which
is during scenario setup, and an ability factory that refuses its arguments
there takes the whole engine down -- Enchantress could not be started
because Puppet Master asked for something its factory asserts against.
Building all of them here finds that before a game does.
"""
import importlib
from pathlib import Path
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.version import Ver

PACKS = Path(__file__).resolve().parent.parent / 'cards' / 'pack'


def card_modules():
    for path in sorted(PACKS.rglob('*.py')):
        if path.name == '__init__.py' or '__pycache__' in path.parts:
            continue
        relative = path.relative_to(PACKS.parent.parent).with_suffix('')
        yield '.'.join(relative.parts)


class EveryCardBuildsAbilitiesTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def test_every_card_script_builds_its_abilities(self):
        failures = []
        count = 0
        for name in card_modules():
            try:
                module = importlib.import_module(name)
            except Exception as exc:
                failures.append(f'{name}: import failed: {exc!r}')
                continue
            build = getattr(module, 'GetAbilities', None)
            if build is None:
                continue
            count += 1
            try:
                abilities = build()
            except Exception as exc:
                failures.append(f'{name}: {exc!r}')
                continue
            if abilities is None:
                failures.append(f'{name}: GetAbilities returned None')
        self.assertGreater(count, 1000)
        self.assertEqual(failures, [], '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
