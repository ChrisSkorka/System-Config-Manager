# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock, call, patch

from sysconf.commands.apply_command import ApplyCommand, ApplyFailureResolution
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.actions import ShellAction
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.config.serialization import YamlSerializer
from sysconf.system.error_handler import PromptUserErrorHandler
from sysconf.system.file import FileReader, FileWriter
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.config_location import ConfigLocationWriter
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.system.mock_error_handler import MockSuccessErrorHandler
from test.system.mock_system_executor import MockSystemExecutor
from test.system.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.utils.mock_context import MockContext
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter
from test.utils.mock_path import MockPath, dpath, fpath


RENDERER = SystemConfigRenderer()
SERIALIZER = YamlSerializer()
FILE_READER = FileReader()
FILE_WRITER = FileWriter()
CONFIG_LOCATION_WRITER = ConfigLocationWriter(
    MockDefaults(),
    MockFileReader({}),
    FILE_WRITER,
)

OLD_CONFIG_YAML = dedent('''
    version: "1"
    config: []
''').lstrip()
NEW_CONFIG_YAML = dedent('''
    version: "1"
    config:
      - apt:
          - git
''').lstrip()
EMPTY_CONFIG = SystemConfig.create_from_entries((), (), (), ())
CONFIG_READER = ConfigReader(
    MockFileReader({
        '/old.yaml': OLD_CONFIG_YAML,
        '/new.yaml': NEW_CONFIG_YAML,
    }),
)
OLD_CONFIG = CONFIG_READER.load(Path('/old.yaml'))
NEW_CONFIG = CONFIG_READER.load(Path('/new.yaml'))


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
        self.assertIn('execute', help_text)

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
        fixture_comparative_parser: ComparativeConfigCommandParser
        input_parsed_arguments: Namespace
        expected_old_path: Path
        expected_new_path: Path
        expected_config_path_argument: Path | None

    @datasets({
        'both paths provided': CreateFromArgumentsDataset(
            fixture_comparative_parser=ComparativeConfigCommandParser(
                old_path=fpath('/manual/old.yaml'),
                new_path=fpath('/manual/new.yaml'),
                file_reader=FILE_READER,
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
            expected_config_path_argument=fpath('/manual/new.yaml'),
        ),
        'no old config': CreateFromArgumentsDataset(
            fixture_comparative_parser=ComparativeConfigCommandParser(
                old_path=MockPath('/default/old.yaml'),
                new_path=fpath('/default/new.yaml'),
                file_reader=FILE_READER,
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=MockPath('/default/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
            expected_config_path_argument=None,
        ),
    })
    @patch('sysconf.commands.apply_command.ApplyCommand.create_from_context')
    @patch('sysconf.commands.comparative_config_command_parser.ComparativeConfigCommandParser.create_from_arguments')
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
        mock_create_from_arguments: MagicMock,
        mock_create_from_context: MagicMock,
    ) -> None:
        """Test that the parsed paths are passed on to create_from_context."""

        # Arrange
        mock_create_from_arguments.return_value = dataset.fixture_comparative_parser
        context = MockContext.create()

        # Act
        actual = ApplyCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIs(actual, mock_create_from_context.return_value)
        mock_create_from_arguments.assert_called_once_with(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )
        mock_create_from_context.assert_called_once_with(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
            config_path_argument=dataset.expected_config_path_argument,
        )

    @dataclass
    class CreateFromContextDataset:
        fixture_files: dict[str, str]
        input_old_path: Path
        input_new_path: Path
        input_config_path_argument: Path | None
        expected_old_config: SystemConfig
        expected_new_config: SystemConfig

    @datasets({
        'old config exists': CreateFromContextDataset(
            fixture_files={
                '/manual/old.yaml': OLD_CONFIG_YAML,
                '/manual/new.yaml': NEW_CONFIG_YAML,
            },
            input_old_path=fpath('/manual/old.yaml'),
            input_new_path=fpath('/manual/new.yaml'),
            input_config_path_argument=fpath('/manual/new.yaml'),
            expected_old_config=OLD_CONFIG,
            expected_new_config=NEW_CONFIG,
        ),
        'no old config': CreateFromContextDataset(
            fixture_files={
                '/manual/new.yaml': NEW_CONFIG_YAML,
            },
            input_old_path=MockPath('/manual/old.yaml'),
            input_new_path=fpath('/manual/new.yaml'),
            input_config_path_argument=None,
            expected_old_config=EMPTY_CONFIG,
            expected_new_config=NEW_CONFIG,
        ),
    })
    def test_create_from_context(self, dataset: CreateFromContextDataset) -> None:
        """Test that the configs are loaded and the context's collaborators are used."""

        # Arrange
        defaults = MockDefaults(
            old_config_path=MockPath('/config/.history/current.yaml'),
        )
        file_reader = MockFileReader(dataset.fixture_files)
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = MockContext.create(
            defaults=defaults,
            file_reader=file_reader,
            file_writer=file_writer,
            system_executor=system_executor,
        )
        error_handler = MockSuccessErrorHandler()
        expected_manager = SystemManager(
            old_config=dataset.expected_old_config,
            new_config=dataset.expected_new_config,
            executor=system_executor,
            error_handler=error_handler,
        )
        expected_config_location_writer = ConfigLocationWriter(
            defaults,
            file_reader,
            file_writer,
        )

        # Act
        actual = ApplyCommand.create_from_context(
            context=context,
            old_path=dataset.input_old_path,
            new_path=dataset.input_new_path,
            config_path_argument=dataset.input_config_path_argument,
        )

        # Assert
        self.assertEqual(expected_manager, actual.manager)
        self.assertIs(system_executor, actual.manager.executor)
        self.assertIsInstance(
            actual.manager.error_handler,
            PromptUserErrorHandler,
        )
        self.assertEqual(defaults.get_old_config_path(), actual.current_path)
        self.assertIs(file_writer, actual.file_writer)
        self.assertEqual(
            expected_config_location_writer,
            actual.config_location_writer,
        )
        self.assertEqual(
            dataset.input_config_path_argument,
            actual.config_path_argument,
        )

    @dataclass
    class RunDataset:
        fixture_system_manager: MockSystemManager[ApplyFailureResolution]
        expected_prints: list[str]

    @datasets({
        'no changes required': RunDataset(
            fixture_system_manager=MockSystemManager[ApplyFailureResolution]
            .default(get_actions=[]),
            expected_prints=['# No changes required.'],
        ),
        'gsettings add and update': RunDataset(
            fixture_system_manager=MockSystemManager[ApplyFailureResolution].default(get_actions=[
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
            fixture_system_manager=MockSystemManager[ApplyFailureResolution].default(get_actions=[
                MockDomainAction('Remove gsettings: font-size'),
            ]),
            expected_prints=[
                '# Remove gsettings: font-size',
            ],
        ),
        'dconf add and remove': RunDataset(
            fixture_system_manager=MockSystemManager[ApplyFailureResolution].default(get_actions=[
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
            fixture_system_manager=MockSystemManager[ApplyFailureResolution].default(get_actions=[
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
            current_path=MockPath(
                '/tmp/current.yaml',
                is_file=False,
                exists=False,
            ),
            file_writer=MagicMock(),
            config_location_writer=CONFIG_LOCATION_WRITER,
            config_path_argument=None,
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
        fixture_system_manager: MockSystemManager[ApplyFailureResolution]
        fixture_serialized_config: str
        input_current_path: MockPath

    @datasets({
        'no changes still writes the current config': WriteDataset(
            fixture_system_manager=MockSystemManager[ApplyFailureResolution]
            .default(get_actions=[]),
            fixture_serialized_config='version: 1\nconfig: []\n',
            input_current_path=MockPath(
                '/config/.history/current.yaml', is_file=False, exists=False),
        ),
        'changes are written after the actions run': WriteDataset(
            fixture_system_manager=MockSystemManager[ApplyFailureResolution].default(get_actions=[
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
            config_location_writer=CONFIG_LOCATION_WRITER,
            config_path_argument=None,
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
            manager=MockSystemManager[ApplyFailureResolution]
            .default(get_actions=[]),
            system_config_renderer=MagicMock(),
            yaml_serializer=mock_serializer,
            current_path=dataset.input_current_path,
            file_writer=mock_file_writer,
            config_location_writer=CONFIG_LOCATION_WRITER,
            config_path_argument=None,
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
    class RecordConfigLocationDataset:
        fixture_defaults: MockDefaults
        fixture_file_reader: MockFileReader
        input_config_path_argument: Path | None
        expected_prints: list[str]
        expected_written_files: dict[str, str]

    @datasets({
        'path given and nothing recorded': RecordConfigLocationDataset(
            fixture_defaults=MockDefaults(
                config_location_path=MockPath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            input_config_path_argument=fpath('/manual/new.yaml'),
            expected_prints=[
                'Saved "/manual/new.yaml" as your config location',
                '# No changes required.',
            ],
            expected_written_files={
                '/config/config': '/manual/new.yaml\n',
            },
        ),
        'no path given': RecordConfigLocationDataset(
            fixture_defaults=MockDefaults(
                config_location_path=MockPath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            input_config_path_argument=None,
            expected_prints=[
                '# No changes required.',
            ],
            expected_written_files={},
        ),
        'recorded location is a directory': RecordConfigLocationDataset(
            fixture_defaults=MockDefaults(
                config_location_path=dpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            input_config_path_argument=fpath('/manual/new.yaml'),
            expected_prints=[
                '# No changes required.',
            ],
            expected_written_files={},
        ),
    })
    def test_run_records_the_config_location(
        self,
        dataset: RecordConfigLocationDataset,
    ) -> None:
        """Test that the config location is recorded and reported to the user."""

        # Arrange
        location_file_writer = MockFileWriter()
        apply_command = ApplyCommand(
            manager=MockSystemManager[ApplyFailureResolution]
            .default(get_actions=[]),
            system_config_renderer=MagicMock(),
            yaml_serializer=MagicMock(),
            current_path=MockPath('/config/.history/current.yaml'),
            file_writer=MagicMock(),
            config_location_writer=ConfigLocationWriter(
                dataset.fixture_defaults,
                dataset.fixture_file_reader,
                location_file_writer,
            ),
            config_path_argument=dataset.input_config_path_argument,
        )

        # Act
        with patch('builtins.print') as mock_print:
            apply_command.run()

        # Assert
        self.assertEqual(
            [c.args[0] for c in mock_print.call_args_list],
            dataset.expected_prints,
        )
        self.assertEqual(
            location_file_writer.written_files,
            dataset.expected_written_files,
        )

    @dataclass
    class EqualityDataset:
        input_command: ApplyCommand
        input_other: Any
        expected_equal: bool

    @datasets({
        'same collaborators and path': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            expected_equal=True,
        ),
        'different current path': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/other/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            expected_equal=False,
        ),
        'different manager configs': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(
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
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            expected_equal=False,
        ),
        'different renderer instance': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=SystemConfigRenderer(),
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            expected_equal=False,
        ),
        'different config path argument': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
            ),
            input_other=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=fpath('/manual/new.yaml'),
            ),
            expected_equal=False,
        ),
        'not equal to a string': EqualityDataset(
            input_command=ApplyCommand(
                manager=MockSystemManager[ApplyFailureResolution].default(),
                system_config_renderer=RENDERER,
                yaml_serializer=SERIALIZER,
                current_path=fpath('/config/current.yaml'),
                file_writer=FILE_WRITER,
                config_location_writer=CONFIG_LOCATION_WRITER,
                config_path_argument=None,
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
