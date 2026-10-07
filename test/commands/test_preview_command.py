# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import PurePath
from textwrap import dedent
from unittest.mock import MagicMock

from sysconf.commands.preview_command import PreviewCommand
from sysconf.config.actions import ShellAction
from sysconf.config.system_config import RunActionsResult, SystemConfig, SystemManager
from sysconf.interaction.error_handler import FailingErrorHandler
from sysconf.system.context import Context
from sysconf.system.executor import PreviewSystemExecutor
from test.config.mock_system_manager import MockSystemManager
from test.datasets import datasets
from test.storage.default_paths import DEFAULT_OLD_CONFIG_PATH
from test.system.mock_file import MockFileReader, MockFileWriter
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


class TestPreviewCommand(TestCase):

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = PreviewCommand.get_name()

        # Assert
        self.assertEqual(result, 'preview')

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = PreviewCommand.get_subparser(subparsers)

        # Assert
        self.assertEqual(actual.prog, 'sysconf preview')
        self.assertIn(
            'Preview planned actions without executing',
            parser.format_help(),
        )

    def test_add_arguments(self) -> None:
        """Test that add_arguments adds the expected arguments to the parser."""

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = PreviewCommand.add_arguments(parser)

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

    @datasets({
        'old config exists': CreateFromArgumentsDataset(
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
        expected = PreviewCommand.create_from_context(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
        )

        # Act
        actual = PreviewCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertEqual(expected.manager, actual.manager)

    @dataclass
    class CreateFromContextDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        input_old_path: PurePath
        input_new_path: PurePath
        expected_old_config: SystemConfig
        expected_new_config: SystemConfig

    @datasets({
        'old config exists': CreateFromContextDataset(
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
            input_old_path=PurePath('/manual/old.yaml'),
            input_new_path=PurePath('/manual/new.yaml'),
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
            input_old_path=PurePath('/manual/old.yaml'),
            input_new_path=PurePath('/manual/new.yaml'),
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
        """Test that both configs are loaded into a manager that only previews."""

        # Arrange
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=dataset.fixture_file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )
        executor = MockSystemExecutor()
        error_handler = FailingErrorHandler()
        expected_manager = SystemManager(
            old_config=dataset.expected_old_config,
            new_config=dataset.expected_new_config,
            executor=executor,
            error_handler=error_handler,
        )

        # Act
        actual = PreviewCommand.create_from_context(
            context=context,
            old_path=dataset.input_old_path,
            new_path=dataset.input_new_path,
        )

        # Assert
        self.assertEqual(expected_manager, actual.manager)
        self.assertIsInstance(actual.manager.executor, PreviewSystemExecutor)
        self.assertIsInstance(
            actual.manager.error_handler,
            FailingErrorHandler,
        )

    @dataclass
    class RunDataset:
        fixture_result: RunActionsResult[None]

    @datasets({
        'all actions succeed': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries(
                    (ShellAction('echo new'),), (), (), (),
                ),
            ),
        ),
        'an action fails': RunDataset(
            fixture_result=RunActionsResult(
                SystemConfig.create_from_entries(
                    (ShellAction('echo old'),), (), (), (),
                ),
            ),
        ),
    })
    def test_run_returns(self, dataset: RunDataset) -> None:
        """Test that the actions run and the resulting config is serialized."""

        # Arrange
        old_config = SystemConfig.create_from_entries(
            (ShellAction('echo old'),), (), (), (),
        )
        new_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        manager = MockSystemManager[None].default(
            result=dataset.fixture_result,
            old_config=old_config,
            new_config=new_config,
        )
        system_config_renderer = MagicMock()
        yaml_serializer = MagicMock()
        preview_command = PreviewCommand(
            manager=manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
        )

        # Act
        actual = preview_command.run()

        # Assert
        self.assertIsNone(actual)
        self.assertEqual(manager.run_actions_calls, 1)
        system_config_renderer.render_config.assert_called_once_with(
            dataset.fixture_result.system_config,
        )
        yaml_serializer.get_serialized_data.assert_called_once_with(
            system_config_renderer.render_config.return_value,
        )

    @dataclass
    class RaiseDataset:
        fixture_serialization_exception: Exception
        expected_exception: type[Exception]

    @datasets({
        'serialization fails': RaiseDataset(
            fixture_serialization_exception=ValueError('cannot serialize'),
            expected_exception=ValueError,
        ),
    })
    def test_run_raises(self, dataset: RaiseDataset) -> None:
        """Test that a config that can't be serialized is surfaced."""

        # Arrange
        system_config = SystemConfig.create_from_entries(
            (ShellAction('echo new'),), (), (), (),
        )
        result = RunActionsResult[None](system_config)
        manager = MockSystemManager[None].default(result=result)
        system_config_renderer = MagicMock()
        yaml_serializer = MagicMock()
        yaml_serializer.get_serialized_data.side_effect = \
            dataset.fixture_serialization_exception
        preview_command = PreviewCommand(
            manager=manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
        )

        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            preview_command.run()
