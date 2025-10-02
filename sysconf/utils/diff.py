from typing import Generic, Iterable, TypeVar

T = TypeVar('T')


class Diff(Generic[T]):
    """
    Represents the difference between two collections preserving order.

    Notes:
    - The order of elements is preserved
    - intersection keeps the order of `b`
    - union order is first items unique to `a`, then all items of `b`
    """

    def __init__(
        self,
        a: list[T],
        b: list[T],
        exclusive_a: list[T],
        exclusive_b: list[T],
        intersection: list[T],
        union: list[T],
    ):
        self.a = a
        self.b = b
        self.exclusive_a = exclusive_a
        self.exclusive_b = exclusive_b
        self.intersection = intersection
        self.union = union

    @classmethod
    def create_from_iterables(cls, a: Iterable[T], b: Iterable[T]) -> 'Diff[T]':
        """
        Create a Diff object from two iterables, preserving order.
        """
        a = list(a)
        b = list(b)

        exclusive_a = [item for item in a if item not in b]
        exclusive_b = [item for item in b if item not in a]
        intersection = [item for item in b if item in a] # keep order of b
        union = exclusive_a + b # prefer order of b

        return cls(a, b, exclusive_a, exclusive_b, intersection, union)
