# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import PurePath
from textwrap import dedent
from unittest.mock import call, patch

from sysconf.commands.show_command import ShowCommand
from sysconf.utils.context import Context
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase
from test.utils.default_paths import DEFAULT_OLD_CONFIG_PATH
from test.utils.mock_file import MockFileReader, MockFileWriter


class TestShowCommand(TestCase):

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = ShowCommand.get_name()

        # Assert
        self.assertEqual(result, 'show')

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = ShowCommand.get_subparser(subparsers)

        # Assert
        self.assertEqual(actual.prog, 'sysconf show')
        self.assertIn(
            'Prints the last applied System Configuration',
            parser.format_help(),
        )

    @dataclass
    class AddArgumentsDataset:
        input_argv: list[str]
        expected_config_path: PurePath | None

    @datasets({
        'explicit path provided': AddArgumentsDataset(
            input_argv=['/manual/config.yaml'],
            expected_config_path=PurePath('/manual/config.yaml'),
        ),
        'no path': AddArgumentsDataset(
            input_argv=[],
            expected_config_path=None,
        ),
    })
    def test_add_arguments(self, dataset: AddArgumentsDataset) -> None:
        """Test that add_arguments adds the config_path argument to the parser."""

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = ShowCommand.add_arguments(parser)

        # Assert
        self.assertIs(result_parser, parser)

        args = result_parser.parse_args(dataset.input_argv)
        self.assertEqual(args.config_path, dataset.expected_config_path)

    @dataclass
    class CreateFromArgumentsDataset:
        fixture_path_service: MockPathService
        input_parsed_arguments: Namespace
        expected_config_path: PurePath

    @datasets({
        'explicit path provided': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(
                files={'/manual/config.yaml'},
            ),
            input_parsed_arguments=Namespace(
                config_path=PurePath('/manual/config.yaml'),
            ),
            expected_config_path=PurePath('/manual/config.yaml'),
        ),
        'no path': CreateFromArgumentsDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_OLD_CONFIG_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_path=None,
            ),
            expected_config_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
        ),
    })
    def test_create_from_arguments_returns(
        self,
        dataset: CreateFromArgumentsDataset,
    ) -> None:
        """Test creation from arguments, falling back to the default path."""

        # Arrange
        file_reader = MockFileReader({})
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )

        # Act
        actual = ShowCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertEqual(actual.config_path, dataset.expected_config_path)
        self.assertIs(actual.file_reader, context.get_file_reader())

    @dataclass
    class CreateFromArgumentsErrorDataset:
        fixture_path_service: MockPathService
        input_parsed_arguments: Namespace
        expected_exception_message: str

    @datasets({
        'default path does not exist yet': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(),
            input_parsed_arguments=Namespace(
                config_path=None,
            ),
            expected_exception_message=f'File {DEFAULT_OLD_CONFIG_PATH} does not exist',
        ),
        'explicit path is a directory': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_OLD_CONFIG_PATH},
                dirs={'/manual/config.yaml'},
            ),
            input_parsed_arguments=Namespace(
                config_path=PurePath('/manual/config.yaml'),
            ),
            expected_exception_message='Path /manual/config.yaml is not a file',
        ),
    })
    def test_create_from_arguments_raises(
        self,
        dataset: CreateFromArgumentsErrorDataset,
    ) -> None:
        """Test that a missing or invalid config path is rejected."""

        # Arrange
        file_reader = MockFileReader({})
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as error_context:
            ShowCommand.create_from_arguments(
                context=context,
                parsed_arguments=dataset.input_parsed_arguments,
            )

        self.assertEqual(
            str(error_context.exception),
            dataset.expected_exception_message,
        )

    def test_run(self) -> None:
        """Test that run prints the header and the raw configuration file."""

        # Arrange
        config_path = PurePath('/config/current.yaml')
        serialized_config = dedent('''\
            version: '1'
            config: []
            ''')
        file_reader = MockFileReader({
            '/config/current.yaml': serialized_config,
        })
        show_command = ShowCommand(
            config_path=config_path,
            file_reader=file_reader,
        )

        # Act
        with patch('builtins.print') as mock_print:
            actual = show_command.run()

        # Assert
        self.assertIsNone(actual)
        self.assertEqual(
            mock_print.call_args_list,
            [
                call('Listing current system configuration...'),
                call(serialized_config),
            ],
        )
