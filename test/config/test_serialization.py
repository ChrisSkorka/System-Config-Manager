# pyright: strict

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any

from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_file import MockFileReader
from sysconf.config.serialization import YamlDeserializer, YamlSerializer


class TestYamlDeserializer(TestCase):
    """Tests for YamlDeserializer."""

    @dataclass
    class DeserializeDataset:
        input_content: str
        expected_value: Any

    @datasets({
        'empty_string': DeserializeDataset(
            input_content='',
            expected_value=None,
        ),
        'simple_string': DeserializeDataset(
            input_content='"hello"',
            expected_value='hello',
        ),
        'simple_int': DeserializeDataset(
            input_content='42',
            expected_value=42,
        ),
        'simple_float': DeserializeDataset(
            input_content='3.14',
            expected_value=3.14,
        ),
        'simple_bool_true': DeserializeDataset(
            input_content='true',
            expected_value=True,
        ),
        'simple_bool_false': DeserializeDataset(
            input_content='false',
            expected_value=False,
        ),
        'simple_null': DeserializeDataset(
            input_content='null',
            expected_value=None,
        ),
        'simple_list': DeserializeDataset(
            input_content='[1, 2, 3]',
            expected_value=[1, 2, 3],
        ),
        'simple_dict': DeserializeDataset(
            input_content='{a: 1, b: 2}',
            expected_value={'a': 1, 'b': 2},
        ),
        'nested_dict': DeserializeDataset(
            input_content=dedent('''\
                root:
                  child:
                    value: 42
                '''),
            expected_value={'root': {'child': {'value': 42}}},
        ),
        'list_of_dicts': DeserializeDataset(
            input_content=dedent('''\
                - name: item1
                  value: 10
                - name: item2
                  value: 20
                '''),
            expected_value=[{'name': 'item1', 'value': 10},
                            {'name': 'item2', 'value': 20}],
        ),
        'complex_structure': DeserializeDataset(
            input_content=dedent('''\
                config:
                  items:
                    - id: 1
                      name: first
                      tags: [a, b]
                    - id: 2
                      name: second
                      tags: [c, d]
                  metadata:
                    version: 1.0
                    active: true
                '''),
            expected_value={
                'config': {
                    'items': [
                        {'id': 1, 'name': 'first', 'tags': ['a', 'b']},
                        {'id': 2, 'name': 'second', 'tags': ['c', 'd']},
                    ],
                    'metadata': {'version': 1.0, 'active': True},
                },
            },
        ),
    })
    def test_deserializes_yaml_content(self, dataset: DeserializeDataset) -> None:
        """Test deserialization of scalar and complex data structures."""

        # Arrange
        deserializer = YamlDeserializer()

        # Act
        result = deserializer.get_deserialized_data(dataset.input_content)

        # Assert
        self.assertEqual(result, dataset.expected_value)

    @dataclass
    class InterpolateDataset:
        input_data: Any
        input_replacements: dict[str, str]
        expected_result: Any

    @datasets({
        'string_interpolation': InterpolateDataset(
            input_data='path: /home/user/$pwd/config',
            input_replacements={'$pwd': '/etc'},
            expected_result='path: /home/user//etc/config',
        ),
        'string_multiple_replacements': InterpolateDataset(
            input_data='home: $home, work: $work',
            input_replacements={'$home': '/home/user', '$work': '/workspace'},
            expected_result='home: /home/user, work: /workspace',
        ),
        'string_no_replacements': InterpolateDataset(
            input_data='static: value',
            input_replacements={'$missing': 'replacement'},
            expected_result='static: value',
        ),
        'string_empty': InterpolateDataset(
            input_data='',
            input_replacements={'$pwd': '/etc'},
            expected_result='',
        ),
        'list_of_strings': InterpolateDataset(
            input_data=['path: $pwd/a', 'path: $pwd/b'],
            input_replacements={'$pwd': '/etc'},
            expected_result=['path: /etc/a', 'path: /etc/b'],
        ),
        'list_nested': InterpolateDataset(
            input_data=[['a', '$pwd'], ['b', '$pwd']],
            input_replacements={'$pwd': 'root'},
            expected_result=[['a', 'root'], ['b', 'root']],
        ),
        'list_empty': InterpolateDataset(
            input_data=[],
            input_replacements={'$pwd': '/etc'},
            expected_result=[],
        ),
        'dict_values': InterpolateDataset(
            input_data={'path': '$pwd/config', 'other': 'value'},
            input_replacements={'$pwd': '/etc'},
            expected_result={'path': '/etc/config', 'other': 'value'},
        ),
        'dict_nested': InterpolateDataset(
            input_data={'level1': {'level2': '$pwd/file'}},
            input_replacements={'$pwd': '/root'},
            expected_result={'level1': {'level2': '/root/file'}},
        ),
        'dict_keys_not_interpolated': InterpolateDataset(
            input_data={'$pwd': 'value'},
            input_replacements={'$pwd': '/etc'},
            expected_result={'$pwd': 'value'},
        ),
        'dict_empty': InterpolateDataset(
            input_data={},
            input_replacements={'$pwd': '/etc'},
            expected_result={},
        ),
        'mixed_structure': InterpolateDataset(
            input_data={
                'paths': ['$pwd/a', '$pwd/b'],
                'config': {
                    'root': '$pwd',
                    'items': [1, 2, 3],
                },
                'tags': ['static', '$pwd/tag'],
            },
            input_replacements={'$pwd': '/var/lib'},
            expected_result={
                'paths': ['/var/lib/a', '/var/lib/b'],
                'config': {
                    'root': '/var/lib',
                    'items': [1, 2, 3],
                },
                'tags': ['static', '/var/lib/tag'],
            },
        ),
        'nested_list_and_dict': InterpolateDataset(
            input_data=[
                {'path': '$pwd/config'},
                {'items': ['$pwd/a', '$pwd/b']},
            ],
            input_replacements={'$pwd': '/etc'},
            expected_result=[
                {'path': '/etc/config'},
                {'items': ['/etc/a', '/etc/b']},
            ],
        ),
    })
    def test_interpolates_data(self, dataset: InterpolateDataset) -> None:
        """Test interpolation of strings, lists, dicts, and complex structures."""

        # Arrange
        deserializer = YamlDeserializer()

        # Act
        result = deserializer.get_interpolated_data(
            dataset.input_data,
            dataset.input_replacements,
        )

        # Assert
        self.assertEqual(result, dataset.expected_result)

    @dataclass
    class ImmutabilityDataset:
        input_data: Any
        input_replacements: dict[str, str]

    @datasets({
        'scalar_not_mutated': ImmutabilityDataset(
            input_data='original: $pwd/path',
            input_replacements={'$pwd': '/etc'},
        ),
        'list_not_mutated': ImmutabilityDataset(
            input_data=['item1', '$pwd/path'],
            input_replacements={'$pwd': '/etc'},
        ),
        'dict_not_mutated': ImmutabilityDataset(
            input_data={'key': '$pwd/value'},
            input_replacements={'$pwd': '/etc'},
        ),
    })
    def test_does_not_modify_original_data(self, dataset: ImmutabilityDataset) -> None:
        """Test that interpolation does not modify original data structures."""

        # Arrange
        deserializer = YamlDeserializer()
        original_data = dataset.input_data
        original_str = str(original_data)

        # Act
        deserializer.get_interpolated_data(
            original_data,
            dataset.input_replacements,
        )

        # Assert
        self.assertEqual(str(original_data), original_str)

    @dataclass
    class FileDataset:
        input_file_reader: MockFileReader
        fixture_test_path: Path
        expected_result: Any

    @datasets({
        'simple_yaml_file': FileDataset(
            input_file_reader=MockFileReader({
                str(Path('/test/config.yaml')): dedent('''\
                    key: value
                    number: 42
                    '''),
            }),
            fixture_test_path=Path('/test/config.yaml'),
            expected_result={'key': 'value', 'number': 42},
        ),
        'yaml_with_pwd_interpolation': FileDataset(
            input_file_reader=MockFileReader({
                str(Path('/test/config.yaml')): dedent('''\
                    path: $pwd/config
                    other: static
                    '''),
            }),
            fixture_test_path=Path('/test/config.yaml'),
            expected_result={
                'path': f'{Path("/test").expanduser().resolve()}/config',
                'other': 'static',
            },
        ),
        'yaml_list_file': FileDataset(
            input_file_reader=MockFileReader({
                str(Path('/test/config.yaml')): dedent('''\
                    - item1
                    - item2
                    - item3
                    '''),
            }),
            fixture_test_path=Path('/test/config.yaml'),
            expected_result=['item1', 'item2', 'item3'],
        ),
        'yaml_nested_with_pwd': FileDataset(
            input_file_reader=MockFileReader({
                str(Path('/test/config.yaml')): dedent('''\
                    root:
                      config: $pwd/file
                      value: 123
                    '''),
            }),
            fixture_test_path=Path('/test/config.yaml'),
            expected_result={
                'root': {
                    'config': f'{Path("/test").expanduser().resolve()}/file',
                    'value': 123,
                },
            },
        ),
        'pwd_interpolates_to_file_directory': FileDataset(
            input_file_reader=MockFileReader({
                str(Path('/home/user/configs/app.yaml')):
                    'config_dir: $pwd\nconfig_file: $pwd/settings.yaml',
            }),
            fixture_test_path=Path('/home/user/configs/app.yaml'),
            expected_result={
                'config_dir': str(Path('/home/user/configs').expanduser().resolve()),
                'config_file': f'{Path("/home/user/configs").expanduser().resolve()}/settings.yaml',
            },
        ),
    })
    def test_reads_and_interpolates_yaml_from_file(self, dataset: FileDataset) -> None:
        """Test reading and interpolating YAML from file."""

        # Arrange
        deserializer = YamlDeserializer()

        # Act
        result = deserializer.get_data_from_file(
            dataset.input_file_reader,
            dataset.fixture_test_path,
        )

        # Assert
        self.assertEqual(result, dataset.expected_result)


class TestYamlSerializer(TestCase):
    """Tests for YamlSerializer."""

    @dataclass
    class SerializeDataset:
        input_data: Any
        expected_content: str

    @datasets({
        'none': SerializeDataset(
            input_data=None,
            expected_content='null\n...\n',
        ),
        'string': SerializeDataset(
            input_data='hello',
            expected_content='hello\n...\n',
        ),
        'empty_string': SerializeDataset(
            input_data='',
            expected_content="''\n",
        ),
        'int': SerializeDataset(
            input_data=42,
            expected_content='42\n...\n',
        ),
        'float': SerializeDataset(
            input_data=3.14,
            expected_content='3.14\n...\n',
        ),
        'bool_true': SerializeDataset(
            input_data=True,
            expected_content='true\n...\n',
        ),
        'bool_false': SerializeDataset(
            input_data=False,
            expected_content='false\n...\n',
        ),
        'empty_list': SerializeDataset(
            input_data=[],
            expected_content='[]\n',
        ),
        'empty_dict': SerializeDataset(
            input_data={},
            expected_content='{}\n',
        ),
        'simple_list': SerializeDataset(
            input_data=[1, 2, 3],
            expected_content=dedent('''\
                - 1
                - 2
                - 3
                '''),
        ),
        'simple_dict_preserves_key_order': SerializeDataset(
            input_data={'b': 2, 'a': 1},
            expected_content=dedent('''\
                b: 2
                a: 1
                '''),
        ),
        'nested_dict': SerializeDataset(
            input_data={'root': {'child': {'value': 42}}},
            expected_content=dedent('''\
                root:
                  child:
                    value: 42
                '''),
        ),
        'list_of_dicts_preserves_key_order': SerializeDataset(
            input_data=[
                {'name': 'item1', 'value': 10},
                {'name': 'item2', 'value': 20},
            ],
            expected_content=dedent('''\
                - name: item1
                  value: 10
                - name: item2
                  value: 20
                '''),
        ),
        'complex_structure': SerializeDataset(
            input_data={
                'config': {
                    'items': [
                        {'id': 1, 'name': 'first', 'tags': ['a', 'b']},
                        {'id': 2, 'name': 'second', 'tags': ['c', 'd']},
                    ],
                    'metadata': {'version': 1.0, 'active': True},
                },
            },
            expected_content=dedent('''\
                config:
                  items:
                  - id: 1
                    name: first
                    tags:
                    - a
                    - b
                  - id: 2
                    name: second
                    tags:
                    - c
                    - d
                  metadata:
                    version: 1.0
                    active: true
                '''),
        ),
    })
    def test_serializes_data_to_yaml(self, dataset: SerializeDataset) -> None:
        """Test serialization of scalar and complex data structures."""

        # Arrange
        serializer = YamlSerializer()

        # Act
        result = serializer.get_serialized_data(dataset.input_data)

        # Assert
        self.assertEqual(result, dataset.expected_content)

    @dataclass
    class RoundTripDataset:
        input_data: Any

    @datasets({
        'scalar_string': RoundTripDataset(input_data='hello world'),
        'scalar_int': RoundTripDataset(input_data=42),
        'scalar_float': RoundTripDataset(input_data=3.14),
        'scalar_bool': RoundTripDataset(input_data=True),
        'scalar_none': RoundTripDataset(input_data=None),
        'list': RoundTripDataset(input_data=[1, 'two', 3.0, True, None]),
        'dict': RoundTripDataset(
            input_data={'z': 1, 'a': 2, 'm': 3},
        ),
        'nested': RoundTripDataset(
            input_data={
                'config': {
                    'items': [
                        {'id': 1, 'name': 'first', 'tags': ['a', 'b']},
                        {'id': 2, 'name': 'second', 'tags': ['c', 'd']},
                    ],
                    'metadata': {'version': 1.0, 'active': True},
                },
            },
        ),
    })
    def test_round_trip_preserves_data(self, dataset: RoundTripDataset) -> None:
        """Test that serializing then deserializing returns the original data."""

        # Arrange
        serializer = YamlSerializer()
        deserializer = YamlDeserializer()

        # Act
        serialized = serializer.get_serialized_data(dataset.input_data)
        result = deserializer.get_deserialized_data(serialized)

        # Assert
        self.assertEqual(result, dataset.input_data)
