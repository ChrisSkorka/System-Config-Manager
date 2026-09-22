# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

from sysconf.commands.apply_command import ApplyCommand
from sysconf.config.actions import ShellAction
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.system_config import SystemConfig
from sysconf.config.serialization import YamlSerializer
from sysconf.system.file import FileWriter
from test.commands.mock_comparative_config_command_parser import MockComparativeConfigCommandParser
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.system.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.utils.mock_path import MockPath, fpath


RENDERER = SystemConfigRenderer()
SERIALIZER = YamlSerializer()
FILE_WRITER = FileWriter()


class TestApplyCommand(TestCase):
    """
    Test the apply command.

    Note that the renderer, serializer and file writer have no value
    equality, so two commands are only equal when they share those
    instances.
    """

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = ApplyCommand.get_name()

        # Assert
        self.assertIsInstance(result, str)

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = ApplyCommand.get_subparser(subparsers)

        # Assert
        self.assertIsInstance(actual, ArgumentParser)

        help_text = actual.format_help()
        self.assertIn('Apply', help_text)

    def test_add_arguments(self) -> None:
        """Test that add_arguments adds the expected arguments to the parser."""

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = ApplyCommand.add_arguments(parser)

        # Assert
        self.assertIs(result_parser, parser)

        # Test that we can parse arguments (this validates the arguments were added)
        args = parser.parse_args(['test.yaml', '--last-config', 'old.yaml'])
        self.assertEqual(args.config_file, Path('test.yaml'))
        self.assertEqual(args.last_config, Path('old.yaml'))

    @dataclass
    class CreateFromArgumentsDataset:
        fixture_create_from_arguments: MockComparativeConfigCommandParser
        input_parsed_arguments: Namespace
        expected_parsed_arguments: Namespace

    @datasets({
        'both paths provided': CreateFromArgumentsDataset(
            fixture_create_from_arguments=MockComparativeConfigCommandParser.default(
                system_manager=MockSystemManager.default(),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
        ),
        'only new config provided': CreateFromArgumentsDataset(
            fixture_create_from_arguments=MockComparativeConfigCommandParser.default(
                system_manager=MockSystemManager.default(),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=None,
            ),
        ),
        'only old config provided': CreateFromArgumentsDataset(
            fixture_create_from_arguments=MockComparativeConfigCommandParser.default(
                system_manager=MockSystemManager.default(),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_parsed_arguments=Namespace(
                config_file=None,
                last_config=fpath('/manual/old.yaml'),
            ),
        ),
        'no paths provided': CreateFromArgumentsDataset(
            fixture_create_from_arguments=MockComparativeConfigCommandParser.default(
                system_manager=MockSystemManager.default(),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
        ),
    })
    @patch('sysconf.commands.comparative_config_command_parser.ComparativeConfigCommandParser.create_from_arguments')
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
        mock_create_from_arguments: MagicMock,
    ) -> None:
        """Test successful creation from arguments with various input combinations."""

        # Arrange
        mock_create_from_arguments.return_value = dataset.fixture_create_from_arguments

        # Act
        actual = ApplyCommand.create_from_arguments(
            dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIsInstance(actual, ApplyCommand)
        mock_create_from_arguments.assert_called_once_with(
            dataset.expected_parsed_arguments
        )

    @dataclass
    class RunDataset:
        fixture_system_manager: MockSystemManager
        expected_prints: list[str]

    @datasets({
        'no changes required': RunDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[]),
            expected_prints=['# No changes required.'],
        ),
        'gsettings add and update': RunDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[
                MockDomainAction(
                    'Update gsettings: theme = old_value -> new_value'),
                MockDomainAction('Add gsettings: font-size = 12'),
            ]),
            expected_prints=[
                '# Update gsettings: theme = old_value -> new_value',
                '# Add gsettings: font-size = 12',
            ],
        ),
        'gsettings remove': RunDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[
                MockDomainAction('Remove gsettings: font-size'),
            ]),
            expected_prints=[
                '# Remove gsettings: font-size',
            ],
        ),
        'dconf add and remove': RunDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[
                MockDomainAction('Remove dconf: /path/to/key2'),
                MockDomainAction(
                    'Update dconf: /path/to/key1 = old_value -> new_value'),
                MockDomainAction('Add dconf: /path/to/key3 = new_value3'),
            ]),
            expected_prints=[
                '# Remove dconf: /path/to/key2',
                '# Update dconf: /path/to/key1 = old_value -> new_value',
                '# Add dconf: /path/to/key3 = new_value3',
            ],
        ),
        'mixed domains': RunDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[
                MockDomainAction(
                    'Update gsettings: theme = old_value -> new_value'),
                MockDomainAction('Add dconf: /path/to/key = dconf_value'),
            ]),
            expected_prints=[
                '# Update gsettings: theme = old_value -> new_value',
                '# Add dconf: /path/to/key = dconf_value',
            ],
        ),
    })
    def test_run(
        self,
        dataset: RunDataset,
    ) -> None:
        """Test that run executes the correct commands and produces expected output."""

        # Arrange
        apply_command = ApplyCommand(
            manager=dataset.fixture_system_manager,
            system_config_renderer=MagicMock(),
            yaml_serializer=MagicMock(),
            current_path=MockPath('/tmp/current.yaml', is_file=False, exists=False),
            file_writer=MagicMock(),
        )

        # Act
        with patch('builtins.print') as mock_print:
            apply_command.run()

        # Assert
        mock_print.assert_has_calls(
            [call(p) for p in dataset.expected_prints],
            any_order=False,
        )

    @dataclass
    class WriteDataset:
        fixture_system_manager: MockSystemManager
        fixture_serialized_config: str
        input_current_path: MockPath

    @datasets({
        'no changes still writes the current config': WriteDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[]),
            fixture_serialized_config='version: 1\nconfig: []\n',
            input_current_path=MockPath(
                '/config/.history/current.yaml', is_file=False, exists=False),
        ),
        'changes are written after the actions run': WriteDataset(
            fixture_system_manager=MockSystemManager.default(get_actions=[
                MockDomainAction('Add gsettings: font-size = 12'),
            ]),
            fixture_serialized_config='version: 1\nconfig:\n  - gsettings: {}\n',
            input_current_path=MockPath(
                '/config/.history/current.yaml', is_file=True, exists=True),
        ),
    })
    def test_run_writes_the_rendered_config(self, dataset: WriteDataset) -> None:
        """Test that the rendered config is serialized and written to disk."""

        # Arrange
        mock_renderer = MagicMock()
        mock_serializer = MagicMock()
        mock_serializer.get_serialized_data.return_value = \
            dataset.fixture_serialized_config
        mock_file_writer = MagicMock()

        apply_command = ApplyCommand(
            manager=dataset.fixture_system_manager,
            system_config_renderer=mock_renderer,
            yaml_serializer=mock_serializer,
            current_path=dataset.input_current_path,
            file_writer=mock_file_writer,
        )

        # Act
        with patch('builtins.print'):
            apply_command.run()

        # Assert
        mock_renderer.render_config.assert_called_once_with(
            dataset.fixture_system_manager.new_config,
        )
        mock_serializer.get_serialized_data.assert_called_once_with(
            mock_renderer.render_config.return_value,
        )
        mock_file_writer.write_file_contents.assert_called_once_with(
            dataset.input_current_path,
            dataset.fixture_serialized_config,
        )

    @dataclass
    class WriteFailureDataset:
        fixture_exception: Exception
        fixture_serialized_config: str
        input_current_path: MockPath
        expected_print_calls: list[Any]

    @datasets({
        'permission denied': WriteFailureDataset(
            fixture_exception=PermissionError('Permission denied'),
            fixture_serialized_config='version: 1\nconfig: []\n',
            input_current_path=MockPath(
                '/config/.history/current.yaml', is_file=False, exists=False),
            expected_print_calls=[
                call('Current System Configuration:'),
                call('version: 1\nconfig: []\n'),
                call(),
                call('The changes were successfully applied to the system, '
                     + 'but an error occurred while writing the updated current configuration file:'),
                call('Permission denied'),
                call('Please copy the above configuration and save it to '
                     + '/config/.history/current.yaml.'),
            ],
        ),
        'directory missing': WriteFailureDataset(
            fixture_exception=OSError('No such file or directory'),
            fixture_serialized_config='version: 1\n',
            input_current_path=MockPath(
                '/missing/current.yaml', is_file=False, exists=False),
            expected_print_calls=[
                call('Current System Configuration:'),
                call('version: 1\n'),
                call(),
                call('The changes were successfully applied to the system, '
                     + 'but an error occurred while writing the updated current configuration file:'),
                call('No such file or directory'),
                call('Please copy the above configuration and save it to '
                     + '/missing/current.yaml.'),
            ],
        ),
    })
    def test_run_reports_a_failed_write(
        self,
        dataset: WriteFailureDataset,
    ) -> None:
        """Test that a failed write prints the config for the user to save."""

        # Arrange
        mock_serializer = MagicMock()
        mock_serializer.get_serialized_data.return_value = \
            dataset.fixture_serialized_config
        mock_file_writer = MagicMock()
        mock_file_writer.write_file_contents.side_effect = dataset.fixture_exception

        apply_command = ApplyCommand(
            manager=MockSystemManager.default(get_actions=[]),
            system_config_renderer=MagicMock(),
            yaml_serializer=mock_serializer,
            current_path=dataset.input_current_path,
            file_writer=mock_file_writer,
        )

        # Act
        with patch('builtins.print') as mock_print:
            apply_command.run()

        # Assert
        mock_print.assert_has_calls(
            dataset.expected_print_calls,
            any_order=False,
        )

    @dataclass
    class EqualityDataset:
        input_command: ApplyCommand
        input_other: Any
        expected_equal: bool

    @datasets({
        'same collaborators and path': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            expected_equal=True,
        ),
        'different current path': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/other/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            expected_equal=False,
        ),
        'different manager configs': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager.default(
                    new_config=SystemConfig.create_from_entries(
                        before_actions=(ShellAction('echo hi'),),
                        after_actions=(),
                        config_entries=(),
                        user_domains=(),
                    ),
                ),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            expected_equal=False,
        ),
        'different renderer instance': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=SystemConfigRenderer(),
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            expected_equal=False,
        ),
        'not equal to a string': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager.default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
            ),
            input_other='apply',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that commands compare by manager, path and collaborators."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_command, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_command, dataset.input_other)
