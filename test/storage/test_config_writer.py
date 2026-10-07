# pyright: strict

from dataclasses import dataclass
from pathlib import PurePath
from textwrap import dedent
from unittest.mock import MagicMock

from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.settings import ToolSettings
from sysconf.config.system_config import SystemConfig
from sysconf.storage.config_writer import ConfigWriter
from test.datasets import datasets
from test.system.mock_file import MockFileWriter
from test.test_case import TestCase


class TestConfigWriter(TestCase):
    """Test writing the rendered config to a file."""

    @dataclass
    class WriteDataset:
        input_config: SystemConfig
        input_path: PurePath
        expected_written_files: dict[str, str]

    @datasets({
        'no settings': WriteDataset(
            input_config=SystemConfig.create_from_entries((), (), (), ()),
            input_path=PurePath('/config/.history/current.yaml'),
            expected_written_files={
                '/config/.history/current.yaml': dedent('''\
                    version: '1'
                    system-config-manager:
                      editor: null
                    before: []
                    after: []
                    config: []
                    domains: {}
                    '''),
            },
        ),
        'editor set': WriteDataset(
            input_config=SystemConfig.create_from_entries(
                (), (), (), (),
                settings=ToolSettings(editor='nano'),
            ),
            input_path=PurePath('/other/config.yaml'),
            expected_written_files={
                '/other/config.yaml': dedent('''\
                    version: '1'
                    system-config-manager:
                      editor: nano
                    before: []
                    after: []
                    config: []
                    domains: {}
                    '''),
            },
        ),
    })
    def test_write_returns(self, dataset: WriteDataset) -> None:
        """Test that the config is rendered, serialized and written to the path."""

        # Arrange
        file_writer = MockFileWriter()
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )

        # Act
        writer.write(dataset.input_config, dataset.input_path)

        # Assert
        self.assertEqual(
            file_writer.written_files,
            dataset.expected_written_files,
        )

    @dataclass
    class RaiseDataset:
        fixture_write_exception: Exception
        expected_exception: type[Exception]

    @datasets({
        'permission denied': RaiseDataset(
            fixture_write_exception=PermissionError('Permission denied'),
            expected_exception=PermissionError,
        ),
        'directory missing': RaiseDataset(
            fixture_write_exception=FileNotFoundError('No such directory'),
            expected_exception=FileNotFoundError,
        ),
    })
    def test_write_raises(self, dataset: RaiseDataset) -> None:
        """Test that a failed write is left for the caller to report."""

        # Arrange
        file_writer = MagicMock()
        file_writer.write_file_contents.side_effect = dataset.fixture_write_exception
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )
        config = SystemConfig.create_from_entries((), (), (), ())
        path = PurePath('/config/.history/current.yaml')

        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            writer.write(config, path)
