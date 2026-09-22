# pyright: strict

from dataclasses import dataclass
from typing import cast
from unittest.mock import MagicMock

from sysconf.config.serialization import YamlSerializable
from sysconf.domains.dconf import (
    DConfAddAction,
    DConfRemoveAction,
    DConfUpdateAction,
    create_dconf_domain,
    encode_value,
)
from sysconf.domains.map_domain import MapConfigEntry
from test.datasets import datasets
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


DCONF_DOMAIN = create_dconf_domain()


def dconf_entry(
    path: str,
    value: YamlSerializable,
) -> MapConfigEntry[YamlSerializable]:
    """Build a single-key dconf MapConfigEntry (path_depth=1)."""
    return MapConfigEntry(DCONF_DOMAIN, (path,), value)


class TestEncodeValue(TestCase):
    """Test encoding of YamlSerializable values into dconf strings."""

    @dataclass
    class EncodeDataset:
        input_value: YamlSerializable
        expected_encoded: str

    @datasets({
        'none': EncodeDataset(
            input_value=None,
            expected_encoded='<@mb nothing>',
        ),
        'bool true': EncodeDataset(
            input_value=True,
            expected_encoded='true',
        ),
        'bool false': EncodeDataset(
            input_value=False,
            expected_encoded='false',
        ),
        'positive int': EncodeDataset(
            input_value=42,
            expected_encoded='42',
        ),
        'negative int': EncodeDataset(
            input_value=-7,
            expected_encoded='-7',
        ),
        'float': EncodeDataset(
            input_value=-0.2,
            expected_encoded='-0.2',
        ),
        'string': EncodeDataset(
            input_value='hello',
            expected_encoded='"hello"',
        ),
        'empty string': EncodeDataset(
            input_value='',
            expected_encoded='""',
        ),
        'empty list': EncodeDataset(
            input_value=[],
            expected_encoded='[]',
        ),
        'list of strings': EncodeDataset(
            input_value=['a', 'b'],
            expected_encoded='["a", "b"]',
        ),
        'list of ints': EncodeDataset(
            input_value=[1, 2, 3],
            expected_encoded='[1, 2, 3]',
        ),
        'dict': EncodeDataset(
            input_value={'key': 'value'},
            expected_encoded='{ "key": "value" }',
        ),
        'nested list in dict': EncodeDataset(
            input_value={'items': [1, 2]},
            expected_encoded='{ "items": [1, 2] }',
        ),
    })
    def test_encode_value(self, dataset: EncodeDataset) -> None:
        """Test that each supported value type encodes to the expected string."""

        # Act
        actual = encode_value(dataset.input_value)

        # Assert
        self.assertEqual(actual, dataset.expected_encoded)

    def test_encode_value_raises_on_unsupported_type(self) -> None:
        """Test that an unsupported value type raises an AssertionError."""

        # Act & Assert
        with self.assertRaises(AssertionError) as context:
            encode_value(cast(YamlSerializable, set()))

        self.assertIn('Unsupported value type', str(context.exception))


class TestDConfAddAction(TestCase):
    """Test DConfAddAction creation, description and execution."""

    @dataclass
    class AddDataset:
        input_new_entry: MapConfigEntry[YamlSerializable]
        expected_description: str
        expected_command: tuple[str, ...]

    @datasets({
        'string value': AddDataset(
            input_new_entry=dconf_entry(
                '/org/gnome/desktop/interface/clock-format', '24h'),
            expected_description='Add dconf: /org/gnome/desktop/interface/clock-format = 24h',
            expected_command=(
                'dconf', 'write',
                '/org/gnome/desktop/interface/clock-format', '"24h"',
            ),
        ),
        'bool value': AddDataset(
            input_new_entry=dconf_entry(
                '/org/gnome/desktop/interface/enable-animations', False),
            expected_description='Add dconf: /org/gnome/desktop/interface/enable-animations = False',
            expected_command=(
                'dconf', 'write',
                '/org/gnome/desktop/interface/enable-animations', 'false',
            ),
        ),
        'list value': AddDataset(
            input_new_entry=dconf_entry(
                '/org/gnome/shell/favorite-apps',
                ['firefox.desktop', 'code.desktop'],
            ),
            expected_description="Add dconf: /org/gnome/shell/favorite-apps = ['firefox.desktop', 'code.desktop']",
            expected_command=(
                'dconf', 'write', '/org/gnome/shell/favorite-apps',
                '["firefox.desktop", "code.desktop"]',
            ),
        ),
    })
    def test_create_and_run(self, dataset: AddDataset) -> None:
        """Test add action encodes the value and writes it via dconf."""

        # Arrange
        action = DConfAddAction.create_from_entry(dataset.input_new_entry)
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertIsNone(action.get_old_entry())
        self.assertEqual(action.get_new_entry(), dataset.input_new_entry)

        assert isinstance(executor.command_mock, MagicMock)
        executor.command_mock.assert_called_once_with(*dataset.expected_command)


class TestDConfUpdateAction(TestCase):
    """Test DConfUpdateAction creation, description and execution."""

    @dataclass
    class UpdateDataset:
        input_old_entry: MapConfigEntry[YamlSerializable]
        input_new_entry: MapConfigEntry[YamlSerializable]
        expected_description: str
        expected_command: tuple[str, ...]

    @datasets({
        'string change': UpdateDataset(
            input_old_entry=dconf_entry(
                '/org/gnome/desktop/interface/clock-format', '12h'),
            input_new_entry=dconf_entry(
                '/org/gnome/desktop/interface/clock-format', '24h'),
            expected_description='Update dconf: /org/gnome/desktop/interface/clock-format = 12h -> 24h',
            expected_command=(
                'dconf', 'write',
                '/org/gnome/desktop/interface/clock-format', '"24h"',
            ),
        ),
        'int change': UpdateDataset(
            input_old_entry=dconf_entry(
                '/org/gnome/desktop/peripherals/mouse/speed', 10),
            input_new_entry=dconf_entry(
                '/org/gnome/desktop/peripherals/mouse/speed', 20),
            expected_description='Update dconf: /org/gnome/desktop/peripherals/mouse/speed = 10 -> 20',
            expected_command=(
                'dconf', 'write',
                '/org/gnome/desktop/peripherals/mouse/speed', '20',
            ),
        ),
    })
    def test_create_and_run(self, dataset: UpdateDataset) -> None:
        """Test update action writes the new encoded value via dconf."""

        # Arrange
        action = DConfUpdateAction.create_from_entries(
            dataset.input_old_entry,
            dataset.input_new_entry,
        )
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertEqual(action.get_old_entry(), dataset.input_old_entry)
        self.assertEqual(action.get_new_entry(), dataset.input_new_entry)

        assert isinstance(executor.command_mock, MagicMock)
        executor.command_mock.assert_called_once_with(*dataset.expected_command)


class TestDConfRemoveAction(TestCase):
    """Test DConfRemoveAction creation, description and execution."""

    @dataclass
    class RemoveDataset:
        input_old_entry: MapConfigEntry[YamlSerializable]
        expected_description: str
        expected_command: tuple[str, ...]

    @datasets({
        'string value': RemoveDataset(
            input_old_entry=dconf_entry(
                '/org/gnome/desktop/interface/clock-format', '24h'),
            expected_description='Remove dconf: /org/gnome/desktop/interface/clock-format = 24h',
            expected_command=(
                'dconf', 'reset',
                '/org/gnome/desktop/interface/clock-format',
            ),
        ),
        'list value': RemoveDataset(
            input_old_entry=dconf_entry(
                '/org/gnome/shell/favorite-apps',
                ['firefox.desktop'],
            ),
            expected_description="Remove dconf: /org/gnome/shell/favorite-apps = ['firefox.desktop']",
            expected_command=(
                'dconf', 'reset', '/org/gnome/shell/favorite-apps',
            ),
        ),
    })
    def test_create_and_run(self, dataset: RemoveDataset) -> None:
        """Test remove action resets the key via dconf (value not sent)."""

        # Arrange
        action = DConfRemoveAction.create_from_entry(dataset.input_old_entry)
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertEqual(action.get_old_entry(), dataset.input_old_entry)
        self.assertIsNone(action.get_new_entry())

        assert isinstance(executor.command_mock, MagicMock)
        executor.command_mock.assert_called_once_with(*dataset.expected_command)
