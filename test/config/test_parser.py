# pyright: strict

from dataclasses import dataclass

from sysconf.config.parser import SystemConfigParser, SystemConfigRenderer
from sysconf.config.serialization import YamlSerializable
from sysconf.config.settings import ToolSettings
from sysconf.config.system_config import SystemConfig
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.test_case import TestCase


class TestSystemConfigParserV1(TestCase):
    """Test parsing of the tool settings in a config."""

    @dataclass
    class ParseDataset:
        input_data: dict[str, YamlSerializable]
        expected: SystemConfig

    @datasets({
        'settings key absent': ParseDataset(
            input_data={'version': '1', 'config': []},
            expected=SystemConfig.create_from_entries((), (), (), ()),
        ),
        'settings mapping empty': ParseDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': {},
            },
            expected=SystemConfig.create_from_entries((), (), (), ()),
        ),
        'settings key empty': ParseDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': None,
            },
            expected=SystemConfig.create_from_entries((), (), (), ()),
        ),
        'editor set': ParseDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': {'editor': 'code --wait'},
            },
            expected=SystemConfig.create_from_entries(
                (), (), (), (),
                settings=ToolSettings(editor='code --wait'),
            ),
        ),
    })
    def test_parse_data_returns(self, dataset: ParseDataset) -> None:
        """Test that the settings key is parsed into the config's settings."""

        # Arrange
        parser = SystemConfigParser.get_parser(dataset.input_data)

        # Act
        actual = parser.parse_data(dataset.input_data)

        # Assert
        self.assertEqual(actual, dataset.expected)

    @dataclass
    class InvalidDataset:
        input_data: dict[str, YamlSerializable]
        expected_message: str

    @datasets({
        'settings are not a mapping': InvalidDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': 'nano',
            },
            expected_message="'system-config-manager' must be a mapping",
        ),
        'editor is not a string': InvalidDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': {'editor': 5},
            },
            expected_message="'system-config-manager.editor' must be a string",
        ),
        'editor is empty': InvalidDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': {'editor': '  '},
            },
            expected_message="'system-config-manager.editor' must not be empty",
        ),
        'unknown setting': InvalidDataset(
            input_data={
                'version': '1',
                'config': [],
                'system-config-manager': {'edtior': 'nano'},
            },
            expected_message="Unknown 'system-config-manager' setting: edtior",
        ),
    })
    def test_parse_data_raises(self, dataset: InvalidDataset) -> None:
        """Test that invalid settings fail validation of the whole config."""

        # Arrange
        parser = SystemConfigParser.get_parser(dataset.input_data)

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            parser.parse_data(dataset.input_data)

        self.assertEqual(str(context.exception), dataset.expected_message)


class TestSystemConfigRenderer(TestCase):
    """Test rendering of the tool settings in a config."""

    @dataclass
    class RenderDataset:
        input_config: SystemConfig
        expected: dict[str, YamlSerializable]

    @datasets({
        'no settings': RenderDataset(
            input_config=SystemConfig.create_from_entries((), (), (), ()),
            expected={
                'version': '1',
                'system-config-manager': {
                    'editor': None,
                },
                'before': [],
                'after': [],
                'config': [],
                'domains': {},
            },
        ),
        'editor set': RenderDataset(
            input_config=SystemConfig.create_from_entries(
                (), (), (), (),
                settings=ToolSettings(
                    editor='"C:/Program Files/Editor/editor.exe" -w',
                ),
            ),
            expected={
                'version': '1',
                'system-config-manager': {
                    'editor': '"C:/Program Files/Editor/editor.exe" -w',
                },
                'before': [],
                'after': [],
                'config': [],
                'domains': {},
            },
        ),
    })
    def test_render_config(self, dataset: RenderDataset) -> None:
        """Test that settings are rendered and parse back to the same config."""

        # Arrange
        renderer = SystemConfigRenderer()

        # Act
        actual = renderer.render_config(dataset.input_config)
        parsed = SystemConfigParser.get_parser(actual).parse_data(actual)

        # Assert
        self.assertEqual(actual, dataset.expected)
        self.assertEqual(parsed, dataset.input_config)
