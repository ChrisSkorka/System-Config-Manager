# pyright: strict

import itertools
from typing import Any, Generic, Iterable, TypeVar, cast

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

    def __init__(
        self,
        old: tuple[T, ...],
        new: tuple[T, ...],
        exclusive_old: tuple[T, ...],
        exclusive_new: tuple[T, ...],
        intersection: tuple[T, ...],
        union: tuple[T, ...],
    ) -> None:
        super().__init__()

        # todo make getters
        self.old = old
        self.new = new
        self.exclusive_old = exclusive_old
        self.exclusive_new = exclusive_new
        self.intersection = intersection
        self.union = union

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Diff):
            return False

        _value: Diff[Any] = cast(Diff[Any], value)

        return self.old == _value.old \
            and self.new == _value.new \
            and self.exclusive_old == _value.exclusive_old \
            and self.exclusive_new == _value.exclusive_new \
            and self.intersection == _value.intersection \
            and self.union == _value.union

    @classmethod
    def create_from_iterables(cls, old_items: Iterable[T], new_items: Iterable[T]) -> 'Diff[T]':
        """
        Create a Diff object from two iterables, preserving order.

        Args:
            old_items: The first sequence of items
            new_items: The second sequence of items
        Returns:
            A Diff object holding lists of items the two sequences have in
            in common, and those they don't.
        """

        old_items = tuple(old_items)
        new_items = tuple(new_items)

        exclusive_old = tuple(
            item for item in old_items if item not in new_items
        )
        exclusive_new = tuple(
            item for item in new_items if item not in old_items
        )
        intersection = tuple(
            # keep order of new_items
            item for item in new_items if item in old_items
        )
        union = tuple(
            # prefer order of new_items
            itertools.chain(exclusive_old, new_items)
        )

        return cls(
            old_items,
            new_items,
            exclusive_old,
            exclusive_new,
            intersection,
            union,
        )
