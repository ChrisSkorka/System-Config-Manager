# pyright: strict

from typing import Generic, Sequence, TypeVar

T = TypeVar('T')


class Diff(Generic[T]):
    """
    Represents the difference between two collections preserving order.

    Notes:
    - The order of elements is preserved
    - intersection keeps the order of `b`
    - union order is first items unique to `a`, then all items of `b` with items
      maintaining their order from their original collections
    - This assumes that the collections do not contain duplicates

    Attributes:
        a: The first collection of items
        b: The second collection of items
        exclusive_a: Items in `a` but not in `b`
        exclusive_b: Items in `b` but not in `a`
        intersection: Items in both `a` and `b`
        union: All items in `a` or `b` (without duplicates)
    """

    __slots__ = (
        'a',
        'b',
        'exclusive_a',
        'exclusive_b',
        'intersection',
        'union',
    )

    def __init__(
        self,
        a: list[T],
        b: list[T],
        exclusive_a: list[T],
        exclusive_b: list[T],
        intersection: list[T],
        union: list[T],
    ) -> None:
        super().__init__()

        self.a = a
        self.b = b
        self.exclusive_a = exclusive_a
        self.exclusive_b = exclusive_b
        self.intersection = intersection
        self.union = union

    @classmethod
    def create_from_iterables(cls, a: Sequence[T], b: Sequence[T]) -> 'Diff[T]':
        """
        Create a Diff object from two iterables, preserving order.

        Args:
            a: The first sequence of items
            b: The second sequence of items
        Returns:
            A Diff object holding lists of items the two sequences have in
            in common, and those they don't.
        """
        a = list(a)
        b = list(b)

        exclusive_a = [item for item in a if item not in b]
        exclusive_b = [item for item in b if item not in a]
        intersection = [item for item in b if item in a]  # keep order of b
        union = exclusive_a + b  # prefer order of b

        return cls(a, b, exclusive_a, exclusive_b, intersection, union)
