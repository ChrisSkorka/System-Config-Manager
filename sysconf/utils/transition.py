# pyright: strict

from typing import Generic, Iterable, Self, TypeVar


T = TypeVar('T')


class SequenceTransitioner(Generic[T]):
    """
    Transitions from one ordered sequence to another one item at a time.

    This tracks the current state of a changing sequence at any time as the new
    sequence is built up from the old list one item at a time.

    Notes:
    - Only supports a monotonic transition from the old list to new (no backtracking)
    - Items cannot be duplicated in either list
    - Internally this will remove or move items from the old list and move them
      or add new ones to the new list
    - The final state will have items in the order:
      - first items that were added/updated in the order they were added/updated
      - then all remaining old items in their original order
    - The current state can be retrieved at any time and reflects the state of
      old items + all updates applied so far
    """

    @classmethod
    def create_from_old_items(cls, old_items: Iterable[T]) -> Self:
        """
        Create a new SequenceTransitioner from the given old items.
        """

        return cls(list(old_items), [])

    def __init__(self, old_items: list[T], new_items: list[T]) -> None:
        super().__init__()

        self.old_items = old_items
        self.new_items = new_items

    def update_item(
        self,
        old_item: T | None,
        new_item: T | None,
    ) -> None:
        """
        Update the list of items by applying the given item diff to
        the old and new lists.

        Notes:
        - Added: 
          - old_item is None, new_item is not None
          - new_item is appended to new_items
        - Updated:
          - old_item is not None, new_item is not None
          - old_item is removed from old_items
          - new_item is appended to new_items
        - Removed:
          - old_item is not None, new_item is None
          - old_item is removed from old_items
        """

        assert old_item is not None or new_item is not None, \
            f'Cannot update item: ' \
            + f'old item: {old_item}, new item: {new_item}'

        if old_item is not None:
            assert old_item in self.old_items, \
                f'Cannot remove item {old_item}, it was not found in the old items list'

            self.old_items.remove(old_item)

        if new_item is not None:
            assert new_item not in self.new_items, \
                f'Cannot add item {new_item}, it already exists in the new items list'

            self.new_items.append(new_item)

    def get_current_items(self) -> tuple[T, ...]:
        """
        Get the current items after applying updates.
        """

        return tuple(self.new_items) + tuple(self.old_items)
