# pyright: strict

from dataclasses import dataclass
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.data import DataStructure, get_flattened_dict
from test.datasets import datasets
from test.test_case import TestCase


class TestGetFlattenedDict(TestCase):

    @dataclass
    class Dataset:
        input_data: YamlSerializable
        input_path_depth: int
        expected: dict[tuple[str, ...], YamlSerializable]

    @datasets({
        'depth 0 returns identity': Dataset(
            input_data={'a': {'b': 1}},
            input_path_depth=0,
            expected={(): {'a': {'b': 1}}},
        ),
        'depth 1 flat dict': Dataset(
            input_data={'a': 1, 'b': 2},
            input_path_depth=1,
            expected={('a',): 1, ('b',): 2},
        ),
        'depth 2 nested dict': Dataset(
            input_data={
                'a': {
                    'b': {'c': 1, 'd': 2},
                    'e': 3,
                },
            },
            input_path_depth=2,
            expected={
                ('a', 'b'): {'c': 1, 'd': 2},
                ('a', 'e'): 3,
            },
        ),
        'None at intermediate level skipped': Dataset(
            input_data={'a': {'b': 1}, 'f': None},
            input_path_depth=2,
            expected={('a', 'b'): 1},
        ),
        'depth 2 None at outer level skipped': Dataset(
            input_data={
                'a': {
                    'b': 1,
                    'c': None,
                },
                'f': None,
            },
            input_path_depth=2,
            expected={
                ('a', 'b'): 1,
                ('a', 'c'): None,
            },
        ),
        'empty dict': Dataset(
            input_data={},
            input_path_depth=1,
            expected={},
        ),
        'depth 1 leaf values are non-dict': Dataset(
            input_data={'x': 'hello', 'y': 42, 'z': True},
            input_path_depth=1,
            expected={('x',): 'hello', ('y',): 42, ('z',): True},
        ),
    })
    def test_get_flattened_dict(self, dataset: Dataset) -> None:
        # Act
        result = get_flattened_dict(dataset.input_data, dataset.input_path_depth)

        # Assert
        self.assertEqual(result, dataset.expected)

    def test_non_dict_at_intermediate_level_raises(self) -> None:
        # Act & Assert
        with self.assertRaises(AssertionError):
            get_flattened_dict({'a': 'not-a-dict'}, path_depth=2)


class TestDataStructure(TestCase):

    @dataclass
    class GetDataset:
        input_data: YamlSerializable
        input_path: tuple[str | int, ...]
        expected: YamlSerializable

    @datasets({
        'empty path returns root': GetDataset(
            input_data={'a': 1},
            input_path=(),
            expected={'a': 1},
        ),
        'string key': GetDataset(
            input_data={'a': 1, 'b': 2},
            input_path=('a',),
            expected=1,
        ),
        'nested string keys': GetDataset(
            input_data={'a': {'b': {'c': 'deep'}}},
            input_path=('a', 'b', 'c'),
            expected='deep',
        ),
        'missing key returns None': GetDataset(
            input_data={'a': 1},
            input_path=('z',),
            expected=None,
        ),
        'path beyond missing key returns None': GetDataset(
            input_data={'a': {'b': 1}},
            input_path=('a', 'x', 'y'),
            expected=None,
        ),
        'int key in list': GetDataset(
            input_data={'a': ['x', 'y', 'z']},
            input_path=('a', 1),
            expected='y',
        ),
        'int key out of bounds returns None': GetDataset(
            input_data={'a': ['x']},
            input_path=('a', 5),
            expected=None,
        ),
        'None node returns None': GetDataset(
            input_data={'a': None},
            input_path=('a', 'b'),
            expected=None,
        ),
    })
    def test_getitem(self, dataset: GetDataset) -> None:
        # Arrange
        ds = DataStructure(dataset.input_data)

        # Act
        result = ds[dataset.input_path]

        # Assert
        self.assertEqual(result, dataset.expected)

    @dataclass
    class SetDataset:
        input_initial: YamlSerializable
        input_path: tuple[str | int, ...]
        input_value: YamlSerializable
        expected_data: YamlSerializable

    @datasets({
        'set root': SetDataset(
            input_initial={},
            input_path=(),
            input_value={'x': 1},
            expected_data={'x': 1},
        ),
        'set string key on existing dict': SetDataset(
            input_initial={'a': 1},
            input_path=('b',),
            input_value=2,
            expected_data={'a': 1, 'b': 2},
        ),
        'set nested string keys creates intermediate dicts': SetDataset(
            input_initial={},
            input_path=('a', 'b', 'c'),
            input_value='leaf',
            expected_data={'a': {'b': {'c': 'leaf'}}},
        ),
        'set list index 0 on new list': SetDataset(
            input_initial={},
            input_path=('a', 0),
            input_value='first',
            expected_data={'a': ['first']},
        ),
        'append to list via index': SetDataset(
            input_initial={'a': ['x']},
            input_path=('a', 1),
            input_value='y',
            expected_data={'a': ['x', 'y']},
        ),
        'does not overwrite existing value': SetDataset(
            input_initial={'a': 'old'},
            input_path=('a',),
            input_value='new',
            expected_data={'a': 'old'},
        ),
        'mixed str/int path': SetDataset(
            input_initial={},
            input_path=('a', 'b', 0),
            input_value='val',
            expected_data={'a': {'b': ['val']}},
        ),
    })
    def test_setitem(self, dataset: SetDataset) -> None:
        # Arrange
        ds = DataStructure(dataset.input_initial)

        # Act
        ds[dataset.input_path] = dataset.input_value

        # Assert
        self.assertEqual(ds.get_data(), dataset.expected_data)

    def test_multiple_sets_build_structure(self) -> None:
        # Arrange
        ds = DataStructure({})

        # Act
        ds[('a', 'b', 0)] = 'value1'
        ds[('a', 'b', 1)] = 'value2'
        ds[('a', 'c')] = 'value3'

        # Assert
        self.assertEqual(ds.get_data(), {
            'a': {
                'b': ['value1', 'value2'],
                'c': 'value3',
            }
        })
