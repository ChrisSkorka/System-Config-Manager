# pyright: strict

from dataclasses import dataclass
from sysconf.utils.transition import SequenceTransitioner
from test.datasets import datasets
from test.test_case import TestCase


class TestSequenceTransitioner(TestCase):
    """Test building the current sequence from the old one item at a time."""

    @dataclass
    class GetCurrentItemsDataset:
        fixture_old_items: list[str]
        input_updates: list[tuple[str | None, str | None]]
        expected: tuple[str, ...]

    @datasets({
        'no updates returns old items': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b', 'c'],
            input_updates=[],
            expected=('a', 'b', 'c'),
        ),
        'add single item prepends to result': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b'],
            input_updates=[(None, 'x')],
            expected=('x', 'a', 'b'),
        ),
        'add multiple items preserves insertion order': GetCurrentItemsDataset(
            fixture_old_items=['a'],
            input_updates=[(None, 'x'), (None, 'y')],
            expected=('x', 'y', 'a'),
        ),
        'update item removes from old and adds to new': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b', 'c'],
            input_updates=[('b', 'B')],
            expected=('B', 'a', 'c'),
        ),
        'remove item removes from old': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b', 'c'],
            input_updates=[('b', None)],
            expected=('a', 'c'),
        ),
        'mixed add update remove': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b', 'c'],
            input_updates=[
                (None, 'x'),
                ('b', 'B'),
                ('a', None),
            ],
            expected=('x', 'B', 'c'),
        ),
        'empty old items with add': GetCurrentItemsDataset(
            fixture_old_items=[],
            input_updates=[(None, 'x'), (None, 'y')],
            expected=('x', 'y'),
        ),
        'remove all old items': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b'],
            input_updates=[('a', None), ('b', None)],
            expected=(),
        ),
        'update preserves old item order for remaining': GetCurrentItemsDataset(
            fixture_old_items=['a', 'b', 'c', 'd'],
            input_updates=[('b', 'B'), ('d', 'D')],
            expected=('B', 'D', 'a', 'c'),
        ),
    })
    def test_get_current_items(self, dataset: GetCurrentItemsDataset) -> None:
        # Arrange
        transitioner = SequenceTransitioner[str].create_from_old_items(dataset.fixture_old_items)

        # Act
        for old_item, new_item in dataset.input_updates:
            transitioner.update_item(old_item, new_item)

        # Assert
        actual = transitioner.get_current_items()
        self.assertEqual(dataset.expected, actual)

    @dataclass
    class DuplicatePreventionDataset:
        fixture_old_items: list[str]
        input_updates: list[tuple[str | None, str | None]]
        expected_error: str

    @datasets({
        'add duplicate raises assertion': DuplicatePreventionDataset(
            fixture_old_items=['a'],
            input_updates=[(None, 'x'), (None, 'x')],
            expected_error='x',
        ),
        'update to existing new_item raises assertion': DuplicatePreventionDataset(
            fixture_old_items=['a', 'b'],
            input_updates=[('a', 'new'), ('b', 'new')],
            expected_error='new',
        ),
        'remove item not in old_items raises assertion': DuplicatePreventionDataset(
            fixture_old_items=['a'],
            input_updates=[('z', None)],
            expected_error='z',
        ),
        'both none raises assertion': DuplicatePreventionDataset(
            fixture_old_items=[],
            input_updates=[(None, None)],
            expected_error='Cannot update item',
        ),
    })
    def test_raises_on_invalid_update(self, dataset: DuplicatePreventionDataset) -> None:
        # Arrange
        transitioner = SequenceTransitioner[str].create_from_old_items(dataset.fixture_old_items)

        # Act & Assert
        with self.assertRaises(AssertionError) as ctx:
            for old_item, new_item in dataset.input_updates:
                transitioner.update_item(old_item, new_item)

        self.assertIn(dataset.expected_error, str(ctx.exception))
