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
        input_a: Sequence[Any]
        input_b: Sequence[Any]
        expected_diff: Diff[Any]

    @datasets({
        'empty lists': DiffDataset(
            input_a=[],
            input_b=[],
            expected_diff=Diff(
                a=(),
                b=(),
                exclusive_a=(),
                exclusive_b=(),
                intersection=(),
                union=(),
            ),
        ),
        'identical lists': DiffDataset(
            input_a=['a', 'b', 'c'],
            input_b=['a', 'b', 'c'],
            expected_diff=Diff(
                a=('a', 'b', 'c'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
        ),
        'completely different lists': DiffDataset(
            input_a=['a', 'b', 'c'],
            input_b=['x', 'y', 'z'],
            expected_diff=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
        ),
        'partial overlap': DiffDataset(
            input_a=['a', 'b', 'c', 'd'],
            input_b=['c', 'd', 'e', 'f'],
            expected_diff=Diff(
                a=('a', 'b', 'c', 'd'),
                b=('c', 'd', 'e', 'f'),
                exclusive_a=('a', 'b'),
                exclusive_b=('e', 'f'),
                intersection=('c', 'd'),
                union=('a', 'b', 'c', 'd', 'e', 'f'),
            ),
        ),
        'a is subset of b': DiffDataset(
            input_a=['b', 'd'],
            input_b=['a', 'b', 'c', 'd', 'e'],
            expected_diff=Diff(
                a=('b', 'd'),
                b=('a', 'b', 'c', 'd', 'e'),
                exclusive_a=(),
                exclusive_b=('a', 'c', 'e'),
                intersection=('b', 'd'),
                union=('a', 'b', 'c', 'd', 'e'),
            ),
        ),
        'b is subset of a': DiffDataset(
            input_a=['a', 'b', 'c', 'd', 'e'],
            input_b=['b', 'd'],
            expected_diff=Diff(
                a=('a', 'b', 'c', 'd', 'e'),
                b=('b', 'd'),
                exclusive_a=('a', 'c', 'e'),
                exclusive_b=(),
                intersection=('b', 'd'),
                union=('a', 'c', 'e', 'b', 'd'),
            ),
        ),
        'single element lists': DiffDataset(
            input_a=['x'],
            input_b=['y'],
            expected_diff=Diff(
                a=('x',),
                b=('y',),
                exclusive_a=('x',),
                exclusive_b=('y',),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'empty a, non-empty b': DiffDataset(
            input_a=[],
            input_b=['x', 'y'],
            expected_diff=Diff(
                a=(),
                b=('x', 'y'),
                exclusive_a=(),
                exclusive_b=('x', 'y'),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'non-empty a, empty b': DiffDataset(
            input_a=['x', 'y'],
            input_b=[],
            expected_diff=Diff(
                a=('x', 'y'),
                b=(),
                exclusive_a=('x', 'y'),
                exclusive_b=(),
                intersection=(),
                union=('x', 'y'),
            ),
        ),
        'preserves order in b': DiffDataset(
            input_a=['c', 'a', 'b'],
            input_b=['a', 'b', 'c'],
            expected_diff=Diff(
                a=('c', 'a', 'b'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
                intersection=('a', 'b', 'c'),  # order from b
                union=('a', 'b', 'c'),  # order from b
            ),
        ),
        'order preservation with mixed elements': DiffDataset(
            input_a=['z', 'y', 'x'],
            input_b=['a', 'x', 'b', 'y', 'c'],
            expected_diff=Diff(
                a=('z', 'y', 'x'),
                b=('a', 'x', 'b', 'y', 'c'),
                exclusive_a=('z',),
                exclusive_b=('a', 'b', 'c'),
                intersection=('x', 'y'),  # order from b
                union=('z', 'a', 'x', 'b', 'y', 'c'),  # exclusive_a + b
            ),
        ),
        'integer types': DiffDataset(
            input_a=[1, 2, 3],
            input_b=[3, 4, 5],
            expected_diff=Diff(
                a=(1, 2, 3),
                b=(3, 4, 5),
                exclusive_a=(1, 2),
                exclusive_b=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
        ),
        'tuples as input': DiffDataset(
            input_a=('a', 'b', 'c'),
            input_b=('b', 'c', 'd'),
            expected_diff=Diff(
                a=('a', 'b', 'c'),
                b=('b', 'c', 'd'),
                exclusive_a=('a',),  # converted to lists internally
                exclusive_b=('d',),
                intersection=('b', 'c'),
                union=('a', 'b', 'c', 'd'),
            ),
        ),
        'range objects as input': DiffDataset(
            input_a=range(1, 4),
            input_b=range(3, 6),
            expected_diff=Diff(
                a=(1, 2, 3),
                b=(3, 4, 5),
                exclusive_a=(1, 2),
                exclusive_b=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
        ),
    })
    def test_create_from_iterables(self, dataset: DiffDataset):
        # Arrange (no setup required)

        # Act
        actual = Diff[Any].create_from_iterables(
            dataset.input_a, 
            dataset.input_b,
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
                a=('a', 'b', 'c'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            expected_equal=True,
        ),
        'different a values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('d', 'e', 'f'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different b values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('p', 'q', 'r'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different exclusive_a values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('d', 'e', 'f'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different exclusive_b values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('p', 'q', 'r'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different intersection values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=('common',),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            expected_equal=False,
        ),
        'different union values': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('a', 'b', 'c', 'x', 'y', 'z'),
            ),
            diff2=Diff(
                a=('a', 'b', 'c'),
                b=('x', 'y', 'z'),
                exclusive_a=('a', 'b', 'c'),
                exclusive_b=('x', 'y', 'z'),
                intersection=(),
                union=('different', 'union'),
            ),
            expected_equal=False,
        ),
        'empty diffs': EqDataset(
            diff1=Diff(
                a=(),
                b=(),
                exclusive_a=(),
                exclusive_b=(),
                intersection=(),
                union=(),
            ),
            diff2=Diff(
                a=(),
                b=(),
                exclusive_a=(),
                exclusive_b=(),
                intersection=(),
                union=(),
            ),
            expected_equal=True,
        ),
        'same order different values': EqDataset(
            diff1=Diff(
                a=('1', '2', '3'),
                b=('3', '4', '5'),
                exclusive_a=('1', '2'),
                exclusive_b=('4', '5'),
                intersection=('3',),
                union=('1', '2', '3', '4', '5'),
            ),
            diff2=Diff(
                a=('6', '7', '8'),
                b=('8', '9', '10'),
                exclusive_a=('6', '7'),
                exclusive_b=('9', '10'),
                intersection=('8',),
                union=('6', '7', '8', '9', '10'),
            ),
            expected_equal=False,
        ),
        'integer vs string types': EqDataset(
            diff1=Diff(
                a=(1, 2, 3),
                b=(3, 4, 5),
                exclusive_a=(1, 2),
                exclusive_b=(4, 5),
                intersection=(3,),
                union=(1, 2, 3, 4, 5),
            ),
            diff2=Diff(
                a=('1', '2', '3'),
                b=('3', '4', '5'),
                exclusive_a=('1', '2'),
                exclusive_b=('4', '5'),
                intersection=('3',),
                union=('1', '2', '3', '4', '5'),
            ),
            expected_equal=False,
        ),
        'other is None': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
                intersection=('a', 'b', 'c'),
                union=('a', 'b', 'c'),
            ),
            diff2=None,
            expected_equal=False,
        ),
        'other is another object': EqDataset(
            diff1=Diff(
                a=('a', 'b', 'c'),
                b=('a', 'b', 'c'),
                exclusive_a=(),
                exclusive_b=(),
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
