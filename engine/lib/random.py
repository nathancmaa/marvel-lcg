from core import *
from engine.lib.mt19937 import Random as R
from engine.config import ConfigVariables

DISABLE_NUMPY_RANDOM = ConfigVariables.Bool('disable_numpy_random', False)
CATEGORY_NAME = "RANDOM"

class Random:
    seed = 0
    counter = 0
    rand = R()

    states: List[Any] = []

    @staticmethod
    def AddCounter():
        from engine.log import Log
        Random.counter += 1
        Log.DebugSilent(CATEGORY_NAME, f"{Random.counter=}")

    @staticmethod
    def SetSeed(seed: int) -> None:
        from engine.log import Log
        Random.seed = seed
        Random.counter = 0
        Log.DebugSilent(CATEGORY_NAME, f"Seed: {seed}")
        if DISABLE_NUMPY_RANDOM.value:
            Random.rand.seed(seed)
        else:
            import numpy.random
            numpy.random.seed(Random.seed)

    @staticmethod
    def RandomSeed() -> int:
        import random
        seed = random.randrange(2**31-2)+1
        Random.SetSeed(seed)
        return seed

    T = TypeVar("T")
    @staticmethod
    def RandomChoice(input_list: Sequence[T]) -> T:
        assert input_list != []
        Random.AddCounter()
        if DISABLE_NUMPY_RANDOM.value:
            return Random.rand.choice_one(input_list)
        else:
            import numpy.random
            Random.states.append(numpy.random.get_state())
            # Draw an index rather than hand numpy the list: it turns a list
            # of tuples -- the modular set identities The Hood picks from --
            # into a 2-D array and refuses it. The index draw consumes the
            # generator exactly as the draw over the list did, so a seed
            # still deals the same cards, and the pick is the caller's own
            # object rather than numpy's copy of it.
            return input_list[int(numpy.random.choice(len(input_list)))]

    @staticmethod
    def RandomChoice2(input_list: Sequence[T], x: int) -> List[T]:
        if x < 0:
            raise ValueError("x cannot be negative.")
        if x > len(input_list):
            raise ValueError("x cannot be greater than the length of the input list.")
        if x == 1:
            return [Random.RandomChoice(input_list)]
        if len(input_list) == x:
            return list(input_list)

        Random.AddCounter()
        if DISABLE_NUMPY_RANDOM.value:
            return Random.rand.choice(list(input_list), size=x, replace=False)
        else:
            import numpy.random
            Random.states.append(numpy.random.get_state())
            return list(numpy.random.choice(input_list, size=x, replace=False)) # type: ignore

    @staticmethod
    def Shuffle(list: List[Any]) -> None:
        Random.AddCounter()
        if DISABLE_NUMPY_RANDOM.value:
            Random.rand.shuffle(list)
        else:
            import numpy.random
            Random.states.append(numpy.random.get_state())
            numpy.random.shuffle(list) # type: ignore

    @staticmethod
    def Undo():
        if DISABLE_NUMPY_RANDOM.value:
            pass
        else:
            import numpy.random
            numpy.random.set_state(Random.states.pop())

