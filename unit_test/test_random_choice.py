"""A random pick works on any list, and a seed still picks the same thing."""
import unittest

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from engine.lib.random import Random


class RandomChoiceTests(unittest.TestCase):

    def test_a_list_of_tuples_can_be_picked_from(self):
        # The Hood's setup picks a modular set by its identity, a (pack,
        # set) tuple. numpy read the list of tuples as a 2-D array and
        # refused it, and the scenario could not be started.
        names = [('hood', 'streets_of_mayhem'), ('hood', 'brothers_grimm'), ('core', 'bomb_scare')]
        Random.SetSeed(7)
        pick = Random.RandomChoice(names)
        self.assertIn(pick, names)
        self.assertIs(pick, names[names.index(pick)])

    def test_a_seed_picks_what_it_always_picked(self):
        # The pick is now drawn as an index; a saved game's seed must still
        # deal the same cards, so the draw must consume the generator as
        # numpy's draw over the list did.
        import numpy.random
        items = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        expected = []
        numpy.random.seed(11)
        for _ in range(20):
            expected.append(str(numpy.random.choice(items)))
        Random.SetSeed(11)
        picked = [Random.RandomChoice(items) for _ in range(20)]
        self.assertEqual(picked, expected)
        # And what comes back is the list's own object, not numpy's copy.
        self.assertIs(type(picked[0]), str)


if __name__ == '__main__':
    unittest.main()
