# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import PurePath
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock, call, patch

from sysconf.commands.apply_command import ApplyCommand, ApplyFailureResolution
from sysconf.commands.command import Command
from sysconf.commands.edit_command import EditCommand
from sysconf.config.actions import ShellAction
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import RunActionsResult, SystemConfig
from sysconf.interaction.error_handler import PromptUserErrorHandler
from sysconf.system.executor import CommandException
from sysconf.storage.config_location import ConfigLocationWriter
from sysconf.storage.config_writer import ConfigWriter
from sysconf.system.context import Context
from sysconf.storage.defaults import Defaults
from test.datasets import datasets
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor
from test.config.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.storage.mock_config_writer import MockConfigWriter
from test.storage.default_paths import (
    DEFAULT_CONFIG_LOCATION_PATH,
    DEFAULT_NEW_CONFIG_PATH,
    DEFAULT_OLD_CONFIG_PATH,
)
from test.system.mock_context import mock_context
from test.system.mock_file import MockFileReader, MockFileWriter


def edit_command_factory() -> EditCommand:
    context = mock_context()
    old_path = PurePath('/config/.history/current.yaml')
    new_path = PurePath('/manual/new.yaml')

    return EditCommand.create_from_context(
        context=context,
        old_path=old_path,
        new_path=new_path,
    )


def make_apply_command(
    old_path: PurePath = PurePath('/config/.history/current.yaml'),
    new_path: PurePath = PurePath('/manual/new.yaml'),
    old_config: SystemConfig = SystemConfig.create_from_entries(
        (ShellAction('echo old'),), (), (), (),
    ),
    config_writer: ConfigWriter = ConfigWriter(
        system_config_renderer=SystemConfigRenderer(),
        yaml_serializer=YamlSerializer(),
        file_writer=MockFileWriter(),
    ),
    should_override_config_path: bool = False,
) -> ApplyCommand:
    """Build an apply command from default collaborators, for equality checks."""

    new_config = SystemConfig.create_from_entries(
        (ShellAction('echo new'),), (), (), (),
    )
    manager = MockSystemManager[ApplyFailureResolution].default(
        old_config=old_config,
        new_config=new_config,
    )
    file_reader = MockFileReader({})
    file_writer = MockFileWriter()
    path_service = MockPathService()
    defaults = Defaults(path_service)
    config_location_writer = ConfigLocationWriter(
        defaults,
        file_reader,
        file_writer,
        path_service,
    )

    return ApplyCommand(
        manager=manager,
        old_path=old_path,
        new_path=new_path,
        config_writer=config_writer,
        config_location_writer=config_location_writer,
        should_override_config_path=should_override_config_path,
        edit_command_factory=edit_command_factory,
    )


class TestApplyCommand(TestCase):
    """Test the apply command."""

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = ApplyCommand.get_name()

        # Assert
        self.assertEqual(result, 'apply')

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = ApplyCommand.get_subparser(subparsers)

        # Assert
        self.assertEqual(actual.prog, 'sysconf apply')
        self.assertIn(
            'Apply the configuration to the system',
            parser.format_help(),
        )

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
        self.assertEqual(args.config_file, PurePath('test.yaml'))
        self.assertEqual(args.last_config, PurePath('old.yaml'))

    @dataclass
    class CreateFromArgumentsDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        input_parsed_arguments: Namespace
        expected_old_path: PurePath
        expected_new_path: PurePath
        expected_should_override_config_path: bool

    @datasets({
        'config file given': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_OLD_CONFIG_PATH, '/manual/new.yaml'},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_OLD_CONFIG_PATH: dedent('''\
                    version: 1
                    before:
                      - echo old
                    config: []
                    '''),
                '/manual/new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath('/manual/new.yaml'),
            expected_should_override_config_path=True,
        ),
        'config file from the config location': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_OLD_CONFIG_PATH, DEFAULT_NEW_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_OLD_CONFIG_PATH: dedent('''\
                    version: 1
                    before:
                      - echo old
                    config: []
                    '''),
                DEFAULT_NEW_CONFIG_PATH: dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath(DEFAULT_NEW_CONFIG_PATH),
            expected_should_override_config_path=False,
        ),
        'old config does not exist yet': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(files={'/manual/new.yaml'}),
            fixture_file_reader=MockFileReader({
                '/manual/new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath('/manual/new.yaml'),
            expected_should_override_config_path=True,
        ),
        'old config given': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(
                files={'/manual/new.yaml', '/manual/old.yaml'},
            ),
            fixture_file_reader=MockFileReader({
                '/manual/old.yaml': dedent('''\
                    version: 1
                    before:
                      - echo old
                    config: []
                    '''),
                '/manual/new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/new.yaml'),
                last_config=PurePath('/manual/old.yaml'),
            ),
            expected_old_path=PurePath('/manual/old.yaml'),
            expected_new_path=PurePath('/manual/new.yaml'),
            expected_should_override_config_path=True,
        ),
    })
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
    ) -> None:
        """Test that the parsed paths are used to create the command."""

        # Arrange
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=dataset.fixture_file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )
        expected = ApplyCommand.create_from_context(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
            should_override_config_path=dataset.expected_should_override_config_path,
        )

        # Act
        actual = ApplyCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertEqual(expected.manager, actual.manager)
        self.assertEqual(
            expected.config_location_writer,
            actual.config_location_writer,
        )
        self.assertEqual(dataset.expected_old_path, actual.old_path)
        self.assertEqual(dataset.expected_new_path, actual.new_path)
        self.assertEqual(
            dataset.expected_should_override_config_path,
            actual.should_override_config_path,
        )

    @dataclass
    class CreateFromContextDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        input_old_path: PurePath
        input_new_path: PurePath
        input_should_override_config_path: bool
        expected_old_config: SystemConfig
        expected_new_config: SystemConfig

    @datasets({
        'old config exists': CreateFromContextDataset(
            fixture_path_service=MockPathService(
                files={'/config/.history/current.yaml', '/manual/new.yaml'},
            ),
            fixture_file_reader=MockFileReader({
                '/config/.history/current.yaml': dedent('''\
                    version: 1
                    before:
                      - echo old
                    config: []
                    '''),
                '/manual/new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_old_path=PurePath('/config/.history/current.yaml'),
            input_new_path=PurePath('/manual/new.yaml'),
            input_should_override_config_path=True,
            expected_old_config=SystemConfig.create_from_entries(
                (ShellAction('echo old'),), (), (), (),
            ),
            expected_new_config=SystemConfig.create_from_entries(
                (ShellAction('echo new'),), (), (), (),
            ),
        ),
        'old config does not exist yet': CreateFromContextDataset(
            fixture_path_service=MockPathService(files={'/manual/new.yaml'}),
            fixture_file_reader=MockFileReader({
                '/manual/new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo new
                    config: []
                    '''),
            }),
            input_old_path=PurePath('/config/.history/current.yaml'),
            input_new_path=PurePath('/manual/new.yaml'),
            input_should_override_config_path=False,
            expected_old_config=SystemConfig.create_from_entries(
                (),
                (),
                (),
                (),
            ),
            expected_new_config=SystemConfig.create_from_entries(
                (ShellAction('echo new'),), (), (), (),
            ),
        ),
    })
    def test_create_from_context(self, dataset: CreateFromContextDataset) -> None:
        """
        Test that the configs are loaded, a failed action offers abort or edit,
        and an edit is offered for the same paths.
        """

        # Arrange
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=dataset.fixture_file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )
        expected_manager = MockSystemManager[ApplyFailureResolution].default(
            old_config=dataset.expected_old_config,
            new_config=dataset.expected_new_config,
        )
        defaults = Defaults(dataset.fixture_path_service)
        expected_config_location_writer = ConfigLocationWriter(
            defaults=defaults,
            file_reader=context.get_file_reader(),
            file_writer=context.get_file_writer(),
            path_service=context.get_path_service(),
        )
        expected_edit_command = EditCommand.create_from_context(
            context=context,
            old_path=dataset.input_old_path,
            new_path=dataset.input_new_path,
        )

        # Act
        actual = ApplyCommand.create_from_context(
            context=context,
            old_path=dataset.input_old_path,
            new_path=dataset.input_new_path,
            should_override_config_path=dataset.input_should_override_config_path,
        )

        # Assert
        self.assertEqual(expected_manager, actual.manager)
        self.assertEqual(dataset.input_old_path, actual.old_path)
        self.assertEqual(dataset.input_new_path, actual.new_path)
        self.assertEqual(
            dataset.input_should_override_config_path,
            actual.should_override_config_path,
        )
        self.assertEqual(
            expected_config_location_writer,
            actual.config_location_writer,
        )
        self.assertIs(
            context.get_file_writer(),
            actual.config_writer.file_writer,
        )
        self.assertIs(context.get_system_executor(), actual.manager.executor)

        error_handler = actual.manager.error_handler
        assert isinstance(error_handler, PromptUserErrorHandler)
        self.assertEqual(error_handler.exceptions, (CommandException,))
        self.assertEqual(
            error_handler.failure_resolutions,
            (ApplyFailureResolution.ABORT, ApplyFailureResolution.EDIT),
        )

        actual_edit_command = actual.edit_command_factory()
        self.assertEqual(expected_edit_command, actual_edit_command)

    @dataclass
    class RunDataset:
        fixture_result: RunActionsResult[ApplyFailureResolution]
        expected_written: list[tuple[SystemConfig, PurePath]]
        expected_next_command: Command | None

    @datasets({
        'all actions succeed': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries(
                    (ShellAction('echo new'),), (), (), (),
                ),
            ),
            expected_written=[(
                SystemConfig.create_from_entries(
                    (ShellAction('echo new'),), (), (), (),
                ),
                PurePath('/config/.history/current.yaml'),
            )],
            expected_next_command=None,
        ),
        'action failed and aborted': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries(
                    (ShellAction('echo old'),), (), (), (),
                ),
                ApplyFailureResolution.ABORT,
            ),
            expected_written=[(
                SystemConfig.create_from_entries(
                    (ShellAction('echo old'),), (), (), (),
                ),
                PurePath('/config/.history/current.yaml'),
            )],
            expected_next_command=None,
        ),
        'action failed and edit chosen': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries((), (), (), ()),
                ApplyFailureResolution.EDIT,
            ),
            expected_written=[(
                SystemConfig.create_from_entries((), (), (), ()),
                PurePath('/config/.history/current.yaml'),
            )],
            expected_next_command=EditCommand.create_from_context(
                context=mock_context(),
                old_path=PurePath('/config/.history/current.yaml'),
                new_path=PurePath('/manual/new.yaml'),
            ),
        ),
        'action failed without a resolution': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries(
                    (ShellAction('echo old'),), (), (), (),
                ),
            ),
            expected_written=[(
                SystemConfig.create_from_entries(
                    (ShellAction('echo old'),), (), (), (),
                ),
                PurePath('/config/.history/current.yaml'),
            )],
            expected_next_command=None,
        ),
    })
    def test_run_returns(self, dataset: RunDataset) -> None:
        """
        Test that the resulting config is written to the old path and the
        chosen failure resolution decides the next command.
        """

        # Arrange
        old_config = SystemConfig.create_from_entries(
            (ShellAction('echo old'),), (), (), (),
        )
        new_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        manager = MockSystemManager[ApplyFailureResolution].default(
            result=dataset.fixture_result,
            old_config=old_config,
            new_config=new_config,
        )
        config_writer = MockConfigWriter.create()
        file_reader = MockFileReader({})
        file_writer = MockFileWriter()
        path_service = MockPathService()
        defaults = Defaults(path_service)
        config_location_writer = ConfigLocationWriter(
            defaults,
            file_reader,
            file_writer,
            path_service,
        )
        old_path = PurePath('/config/.history/current.yaml')
        new_path = PurePath('/manual/new.yaml')
        apply_command = ApplyCommand(
            manager=manager,
            old_path=old_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=False,
            edit_command_factory=edit_command_factory,
        )

        # Act
        with patch('builtins.print') as mock_print:
            actual = apply_command.run()

        # Assert
        self.assertEqual(dataset.expected_next_command, actual)
        self.assertEqual(manager.run_actions_calls, 1)
        self.assertEqual(config_writer.written, dataset.expected_written)
        mock_print.assert_not_called()

    @dataclass
    class WriteFailureDataset:
        fixture_exception: Exception
        input_old_path: PurePath
        expected_print_calls: list[Any]

    @datasets({
        'permission denied': WriteFailureDataset(
            fixture_exception=PermissionError('Permission denied'),
            input_old_path=PurePath('/config/.history/current.yaml'),
            expected_print_calls=[
                call('Failed to write current system configuration to file!'),
                call('Permission denied'),
                call(),
                call('The changes were successfully applied to the system, '
                     + 'but an error occurred while writing the updated configuration file.'),
                call(),
                call('Current System Configuration:'),
                call('```'),
                call(dedent('''\
                    version: '1'
                    system-config-manager:
                      editor: null
                    before:
                    - echo new
                    after: []
                    config: []
                    domains: {}
                    ''')),
                call('```'),
                call(),
                call('Please copy the above configuration and save it to '
                     + '/config/.history/current.yaml.'),
            ],
        ),
        'directory missing': WriteFailureDataset(
            fixture_exception=OSError('No such file or directory'),
            input_old_path=PurePath('/missing/current.yaml'),
            expected_print_calls=[
                call('Failed to write current system configuration to file!'),
                call('No such file or directory'),
                call(),
                call('The changes were successfully applied to the system, '
                     + 'but an error occurred while writing the updated configuration file.'),
                call(),
                call('Current System Configuration:'),
                call('```'),
                call(dedent('''\
                    version: '1'
                    system-config-manager:
                      editor: null
                    before:
                    - echo new
                    after: []
                    config: []
                    domains: {}
                    ''')),
                call('```'),
                call(),
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
        file_writer = MagicMock()
        file_writer.write_file_contents.side_effect = dataset.fixture_exception
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        config_writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )
        old_config = SystemConfig.create_from_entries(
            (ShellAction('echo old'),), (), (), (),
        )
        new_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        manager = MockSystemManager[ApplyFailureResolution].default(
            old_config=old_config,
            new_config=new_config,
        )
        location_file_reader = MockFileReader({})
        location_file_writer = MockFileWriter()
        path_service = MockPathService()
        location_defaults = Defaults(path_service)
        config_location_writer = ConfigLocationWriter(
            location_defaults,
            location_file_reader,
            location_file_writer,
            path_service,
        )
        new_path = PurePath('/manual/new.yaml')
        apply_command = ApplyCommand(
            manager=manager,
            old_path=dataset.input_old_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=False,
            edit_command_factory=edit_command_factory,
        )

        # Act
        with patch('builtins.print') as mock_print:
            actual = apply_command.run()

        # Assert
        self.assertIsNone(actual)
        self.assertEqual(
            mock_print.call_args_list,
            dataset.expected_print_calls,
        )

    @dataclass
    class RecordConfigLocationDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        input_should_override_config_path: bool
        expected_prints: list[str]
        expected_written_files: dict[str, str]

    @datasets({
        'override and nothing recorded': RecordConfigLocationDataset(
            fixture_path_service=MockPathService(),
            fixture_file_reader=MockFileReader({}),
            input_should_override_config_path=True,
            expected_prints=[
                'Saved "/manual/new.yaml" as your config location',
            ],
            expected_written_files={
                DEFAULT_CONFIG_LOCATION_PATH: '/manual/new.yaml\n',
            },
        ),
        'override and same location recorded': RecordConfigLocationDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '/manual/new.yaml\n',
            }),
            input_should_override_config_path=True,
            expected_prints=[],
            expected_written_files={},
        ),
        'no override': RecordConfigLocationDataset(
            fixture_path_service=MockPathService(),
            fixture_file_reader=MockFileReader({}),
            input_should_override_config_path=False,
            expected_prints=[],
            expected_written_files={},
        ),
        'recorded location is a directory': RecordConfigLocationDataset(
            fixture_path_service=MockPathService(
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({}),
            input_should_override_config_path=True,
            expected_prints=[],
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
        old_config = SystemConfig.create_from_entries(
            (ShellAction('echo old'),), (), (), (),
        )
        new_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        manager = MockSystemManager[ApplyFailureResolution].default(
            old_config=old_config,
            new_config=new_config,
        )
        config_writer = MockConfigWriter.create()
        defaults = Defaults(dataset.fixture_path_service)
        config_location_writer = ConfigLocationWriter(
            defaults,
            dataset.fixture_file_reader,
            location_file_writer,
            dataset.fixture_path_service,
        )
        old_path = PurePath('/config/.history/current.yaml')
        new_path = PurePath('/manual/new.yaml')
        apply_command = ApplyCommand(
            manager=manager,
            old_path=old_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=dataset.input_should_override_config_path,
            edit_command_factory=edit_command_factory,
        )

        # Act
        with patch('builtins.print') as mock_print:
            apply_command.run()

        # Assert
        self.assertEqual(
            mock_print.call_args_list,
            [call(text) for text in dataset.expected_prints],
        )
        self.assertEqual(
            location_file_writer.written_files,
            dataset.expected_written_files,
        )

    @dataclass
    class EqualityDataset:
        input_command: ApplyCommand
        input_other: object
        expected_equal: bool

    @datasets({
        'same collaborators and paths': EqualityDataset(
            input_command=make_apply_command(),
            input_other=make_apply_command(),
            expected_equal=True,
        ),
        'different old path': EqualityDataset(
            input_command=make_apply_command(),
            input_other=make_apply_command(
                old_path=PurePath('/other/current.yaml'),
            ),
            expected_equal=False,
        ),
        'different new path': EqualityDataset(
            input_command=make_apply_command(),
            input_other=make_apply_command(
                new_path=PurePath('/other/new.yaml'),
            ),
            expected_equal=False,
        ),
        'different manager configs': EqualityDataset(
            input_command=make_apply_command(),
            input_other=make_apply_command(
                old_config=SystemConfig.create_from_entries((), (), (), ()),
            ),
            expected_equal=False,
        ),
        'different config path override': EqualityDataset(
            input_command=make_apply_command(),
            input_other=make_apply_command(should_override_config_path=True),
            expected_equal=False,
        ),
        'not an apply command': EqualityDataset(
            input_command=make_apply_command(),
            input_other='apply',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that commands compare by manager, paths and collaborators."""

        # Act
        actual = dataset.input_command == dataset.input_other

        # Assert
        self.assertEqual(actual, dataset.expected_equal)

    def test_equality_ignores_the_edit_command_factory(self) -> None:
        """Test that the edit command factory is not compared."""

        # Arrange
        old_config = SystemConfig.create_from_entries(
            (ShellAction('echo old'),), (), (), (),
        )
        new_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        manager = MockSystemManager[ApplyFailureResolution].default(
            old_config=old_config,
            new_config=new_config,
        )

        def other_edit_command_factory() -> EditCommand:
            return edit_command_factory()

        command = make_apply_command()
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        file_writer = MockFileWriter()
        config_writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )
        location_file_reader = MockFileReader({})
        path_service = MockPathService()
        location_defaults = Defaults(path_service)
        config_location_writer = ConfigLocationWriter(
            location_defaults,
            location_file_reader,
            file_writer,
            path_service,
        )
        old_path = PurePath('/config/.history/current.yaml')
        new_path = PurePath('/manual/new.yaml')
        other = ApplyCommand(
            manager=manager,
            old_path=old_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=False,
            edit_command_factory=other_edit_command_factory,
        )

        # Act & Assert
        self.assertEqual(command, other)
