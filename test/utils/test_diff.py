# pyright: strict

from dataclasses import dataclass
from typing import Any, Sequence
from sysconf.utils.diff import Diff
from test.datasets import datasets
from test.test_case import TestCase


class TestDiff(TestCase):
    """Tests for the Diff utility class."""

    @dataclass
    class DiffDataset:
        input_old_items: Sequence[Any]
        input_new_items: Sequence[Any]
        expected_diff: Diff[Any]

    @datasets({
        'empty lists': DiffDataset(
            input_old_items=[],
            input_new_items=[],
            expected_diff=Diff(
                old=(),
                new=(),
                exclusive_old=(),
                exclusive_new=(),
                intersection=(),
                union=(),
            ),
        ),
        'identical lists': DiffDataset(
            input_old_items=['a', 'b', 'c'],
            input_new_items=['a', 'b', 'c'],
            expected_diff=Diff(
                old=('a', 'b', 'c'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
        ),
        'completely different lists': DiffDataset(
            input_old_items=['a', 'b', 'c'],
            input_new_items=['x', 'y', 'z'],
            expected_diff=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
        ),
        'partial overlap': DiffDataset(
            input_old_items=['a', 'b', 'c', 'd'],
            input_new_items=['c', 'd', 'e', 'f'],
            expected_diff=Diff(
                old=('a', 'b', 'c', 'd'),
                new=('c', 'd', 'e', 'f'),
                exclusive_old=('a', 'b'),
                exclusive_new=('e', 'f'),
                intersection=('c', 'd'),
                union=('a', 'b', 'c', 'd', 'e', 'f'),
            ),
        ),
        'a is subset of b': DiffDataset(
            input_old_items=['b', 'd'],
            input_new_items=['a', 'b', 'c', 'd', 'e'],
            expected_diff=Diff(
                old=('b', 'd'),
                new=('a', 'b', 'c', 'd', 'e'),
                exclusive_old=(),
                exclusive_new=('a', 'c', 'e'),
                intersection=('b', 'd'),
                union=('a', 'b', 'c', 'd', 'e'),
            ),
        ),
        'b is subset of a': DiffDataset(
            input_old_items=['a', 'b', 'c', 'd', 'e'],
            input_new_items=['b', 'd'],
            expected_diff=Diff(
                old=('a', 'b', 'c', 'd', 'e'),
                new=('b', 'd'),
                exclusive_old=('a', 'c', 'e'),
                exclusive_new=(),
                intersection=('b', 'd'),
                union=('a', 'c', 'e', 'b', 'd'),
            ),
        ),
        'single element lists': DiffDataset(
            input_old_items=['x'],
            input_new_items=['y'],
            expected_diff=Diff(
                old=('x',),
                new=('y',),
                exclusive_old=('x',),
                exclusive_new=('y',),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'empty a, non-empty b': DiffDataset(
            input_old_items=[],
            input_new_items=['x', 'y'],
            expected_diff=Diff(
                old=(),
                new=('x', 'y'),
                exclusive_old=(),
                exclusive_new=('x', 'y'),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'non-empty a, empty b': DiffDataset(
            input_old_items=['x', 'y'],
            input_new_items=[],
            expected_diff=Diff(
                old=('x', 'y'),
                new=(),
                exclusive_old=('x', 'y'),
                exclusive_new=(),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'preserves order in b': DiffDataset(
            input_old_items=['c', 'a', 'b'],
            input_new_items=['a', 'b', 'c'],
            expected_diff=Diff(
                old=('c', 'a', 'b'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),  # order from b
                union=('a', 'b', 'c'),  # order from b
            ),
        ),
        'order preservation with mixed elements': DiffDataset(
            input_old_items=['z', 'y', 'x'],
            input_new_items=['a', 'x', 'b', 'y', 'c'],
            expected_diff=Diff(
                old=('z', 'y', 'x'),
                new=('a', 'x', 'b', 'y', 'c'),
                exclusive_old=('z',),
                exclusive_new=('a', 'b', 'c'),
                intersection=('x', 'y'),  # order from b
                union=('z', 'a', 'x', 'b', 'y', 'c'),  # exclusive_a + b
            ),
        ),
        'integer types': DiffDataset(
            input_old_items=[1, 2, 3],
            input_new_items=[3, 4, 5],
            expected_diff=Diff(
                old=(1, 2, 3),
                new=(3, 4, 5),
                exclusive_old=(1, 2),
                exclusive_new=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
        ),
        'tuples as input': DiffDataset(
            input_old_items=('a', 'b', 'c'),
            input_new_items=('b', 'c', 'd'),
            expected_diff=Diff(
                old=('a', 'b', 'c'),
                new=('b', 'c', 'd'),
                exclusive_old=('a',),  # converted to lists internally
                exclusive_new=('d',),
                intersection=('b', 'c'),
                union=('a', 'b', 'c', 'd'),
            ),
        ),
        'range objects as input': DiffDataset(
            input_old_items=range(1, 4),
            input_new_items=range(3, 6),
            expected_diff=Diff(
                old=(1, 2, 3),
                new=(3, 4, 5),
                exclusive_old=(1, 2),
                exclusive_new=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
        ),
    })
    def test_create_from_iterables(self, dataset: DiffDataset):
        # Arrange (no setup required)

        # Act
        actual = Diff[Any].create_from_iterables(
            dataset.input_old_items,
            dataset.input_new_items,
        )

        # Assert
        self.assertEqual(actual, dataset.expected_diff)

    @dataclass
    class EqDataset:
        diff1: Diff[Any]
        diff2: Diff[Any] | Any
        expected_equal: bool

    @datasets({
        'identical diffs': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            expected_equal=True,
        ),
        'different a values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('d', 'e', 'f'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different b values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('p', 'q', 'r'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different exclusive_a values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('d', 'e', 'f'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different exclusive_b values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('p', 'q', 'r'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different intersection values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=('common',),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different union values': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                old=('a', 'b', 'c'),
                new=('x', 'y', 'z'),
                exclusive_old=('a', 'b', 'c'),
                exclusive_new=('x', 'y', 'z'),
                intersection=(),
                union=('different', 'union'),
            ),
            expected_equal=False,
        ),
        'empty diffs': EqDataset(
            diff1=Diff(
                old=(),
                new=(),
                exclusive_old=(),
                exclusive_new=(),
                intersection=(),
                union=(),
            ),
            diff2=Diff(
                old=(),
                new=(),
                exclusive_old=(),
                exclusive_new=(),
                intersection=(),
                union=(),
            ),
            expected_equal=True,
        ),
        'same order different values': EqDataset(
            diff1=Diff(
                old=('1', '2', '3'),
                new=('3', '4', '5'),
                exclusive_old=('1', '2'),
                exclusive_new=('4', '5'),
                intersection=('3',),
                union=('1', '2', '3', '4', '5'),
            ),
            diff2=Diff(
                old=('6', '7', '8'),
                new=('8', '9', '10'),
                exclusive_old=('6', '7'),
                exclusive_new=('9', '10'),
                intersection=('8',),
                union=('6', '7', '8', '9', '10'),
            ),
            expected_equal=False,
        ),
        'integer vs string types': EqDataset(
            diff1=Diff(
                old=(1, 2, 3),
                new=(3, 4, 5),
                exclusive_old=(1, 2),
                exclusive_new=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
            diff2=Diff(
                old=('1', '2', '3'),
                new=('3', '4', '5'),
                exclusive_old=('1', '2'),
                exclusive_new=('4', '5'),
                intersection=('3',),
                union=('1', '2', '3', '4', '5'),
            ),
            expected_equal=False,
        ),
        'other is None': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            diff2=None,
            expected_equal=False,
        ),
        'other is another object': EqDataset(
            diff1=Diff(
                old=('a', 'b', 'c'),
                new=('a', 'b', 'c'),
                exclusive_old=(),
                exclusive_new=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            diff2=('a', 'b', 'c'),
            expected_equal=False,
        ),
    })
    def test_eq(self, dataset: EqDataset):
        # Arrange (no setup required)

        # Act
        actual = (dataset.diff1 == dataset.diff2)

        # Assert
        self.assertEqual(actual, dataset.expected_equal)
