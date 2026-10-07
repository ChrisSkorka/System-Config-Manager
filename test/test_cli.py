# pyright: strict

from argparse import Namespace
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Type
from unittest.mock import MagicMock, patch

from sysconf.cli import main
from sysconf.commands.apply_command import ApplyCommand
from sysconf.commands.command import Command
from sysconf.commands.edit_command import EditCommand
from sysconf.commands.preview_command import PreviewCommand
from sysconf.commands.show_command import ShowCommand
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_context import mock_context


class TestMain(TestCase):
    """Test the cli entry point wiring of arguments to commands."""

    @dataclass
    class MainDataset:
        fixture_command_class: Type[Command]
        input_argv: list[str]
        expected_parsed_arguments: Namespace

    @datasets({
        'show with an explicit path': MainDataset(
            fixture_command_class=ShowCommand,
            input_argv=['sysconf', 'show', '/configs/system.yaml'],
            expected_parsed_arguments=Namespace(
                command='show',
                config_path=Path('/configs/system.yaml'),
            ),
        ),
        'show without a path uses the default': MainDataset(
            fixture_command_class=ShowCommand,
            input_argv=['sysconf', 'show'],
            expected_parsed_arguments=Namespace(
                command='show',
                config_path=None,
            ),
        ),
        'preview with a config file': MainDataset(
            fixture_command_class=PreviewCommand,
            input_argv=['sysconf', 'preview', '/configs/new.yaml'],
            expected_parsed_arguments=Namespace(
                command='preview',
                config_file=Path('/configs/new.yaml'),
                last_config=None,
            ),
        ),
        'preview with both configs': MainDataset(
            fixture_command_class=PreviewCommand,
            input_argv=[
                'sysconf', 'preview', '/configs/new.yaml',
                '--last-config', '/configs/old.yaml',
            ],
            expected_parsed_arguments=Namespace(
                command='preview',
                config_file=Path('/configs/new.yaml'),
                last_config=Path('/configs/old.yaml'),
            ),
        ),
        'preview without arguments': MainDataset(
            fixture_command_class=PreviewCommand,
            input_argv=['sysconf', 'preview'],
            expected_parsed_arguments=Namespace(
                command='preview',
                config_file=None,
                last_config=None,
            ),
        ),
        'apply with a config file': MainDataset(
            fixture_command_class=ApplyCommand,
            input_argv=['sysconf', 'apply', '/configs/new.yaml'],
            expected_parsed_arguments=Namespace(
                command='apply',
                config_file=Path('/configs/new.yaml'),
                last_config=None,
            ),
        ),
        'apply with both configs': MainDataset(
            fixture_command_class=ApplyCommand,
            input_argv=[
                'sysconf', 'apply', '/configs/new.yaml',
                '--last-config', '/configs/old.yaml',
            ],
            expected_parsed_arguments=Namespace(
                command='apply',
                config_file=Path('/configs/new.yaml'),
                last_config=Path('/configs/old.yaml'),
            ),
        ),
        'edit with a config file': MainDataset(
            fixture_command_class=EditCommand,
            input_argv=['sysconf', 'edit', '/configs/new.yaml'],
            expected_parsed_arguments=Namespace(
                command='edit',
                config_file=Path('/configs/new.yaml'),
                last_config=None,
            ),
        ),
        'edit without a config file': MainDataset(
            fixture_command_class=EditCommand,
            input_argv=['sysconf', 'edit'],
            expected_parsed_arguments=Namespace(
                command='edit',
                config_file=None,
                last_config=None,
            ),
        ),
    })
    def test_main_runs_the_selected_command(self, dataset: MainDataset) -> None:
        """Test that the sub command is parsed, constructed and run."""

        # Arrange
        context = mock_context()
        mock_command = MagicMock()
        mock_command.run.return_value = None

        # Act
        with patch('sys.argv', dataset.input_argv), \
                patch('sysconf.cli.Context', return_value=context), \
                patch.object(
                    dataset.fixture_command_class,
                    'create_from_arguments',
                    return_value=mock_command,
        ) as mock_create_from_arguments:
            main()

        # Assert
        mock_create_from_arguments.assert_called_once_with(
            context,
            dataset.expected_parsed_arguments,
        )
        mock_command.run.assert_called_once_with()

    @dataclass
    class NextCommandDataset:
        fixture_command_count: int

    @datasets({
        'one command': NextCommandDataset(
            fixture_command_count=1,
        ),
        'three chained commands': NextCommandDataset(
            fixture_command_count=3,
        ),
    })
    def test_main_runs_each_next_command(
        self,
        dataset: NextCommandDataset,
    ) -> None:
        """Test that each command returned by a run is run in turn."""

        # Arrange
        commands = [MagicMock() for _ in range(dataset.fixture_command_count)]
        next_commands = [*commands[1:], None]
        for command, next_command in zip(commands, next_commands):
            command.run.return_value = next_command

        # Act
        with patch('sys.argv', ['sysconf', 'edit']), \
                patch.object(
                    EditCommand,
                    'create_from_arguments',
                    return_value=commands[0],
        ):
            main()

        # Assert
        for command in commands:
            command.run.assert_called_once_with()

    def test_main_without_a_command_prints_help(self) -> None:
        """Test that invoking the cli with no sub command prints the help."""

        # Act
        with patch('sys.argv', ['sysconf']), \
                patch('argparse.ArgumentParser.print_help') as mock_print_help, \
                patch.object(ShowCommand, 'create_from_arguments') as mock_show, \
                patch.object(PreviewCommand, 'create_from_arguments') as mock_preview, \
                patch.object(ApplyCommand, 'create_from_arguments') as mock_apply, \
                patch.object(EditCommand, 'create_from_arguments') as mock_edit:
            main()

        # Assert
        mock_print_help.assert_called_once_with()
        for mock_create in (mock_show, mock_preview, mock_apply, mock_edit):
            mock_create.assert_not_called()

    @dataclass
    class SubparserDataset:
        input_argv: list[str]
        expected_exit_code: int

    @datasets({
        'unknown command': SubparserDataset(
            input_argv=['sysconf', 'not-a-command'],
            expected_exit_code=2,
        ),
        'unknown option': SubparserDataset(
            input_argv=['sysconf', 'apply', '--not-an-option'],
            expected_exit_code=2,
        ),
    })
    def test_main_rejects_invalid_arguments(
        self,
        dataset: SubparserDataset,
    ) -> None:
        """Test that argparse exits with a usage error for invalid input."""

        # Act & Assert
        with patch('sys.argv', dataset.input_argv), \
                patch('sys.stderr'):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, dataset.expected_exit_code)

    @dataclass
    class ValidationErrorDataset:
        fixture_create_error: ValidationError | None
        fixture_run_error: ValidationError | None
        fixture_next_run_error: ValidationError | None
        expected_stderr: str

    @datasets({
        'validation fails while building the command': ValidationErrorDataset(
            fixture_create_error=ValidationError(
                'File /configs/missing.yaml does not exist',
            ),
            fixture_run_error=None,
            fixture_next_run_error=None,
            expected_stderr='Error: File /configs/missing.yaml does not exist\n',
        ),
        'validation fails while running the command': ValidationErrorDataset(
            fixture_create_error=None,
            fixture_run_error=ValidationError(
                "Config must contain a 'version' key",
            ),
            fixture_next_run_error=None,
            expected_stderr="Error: Config must contain a 'version' key\n",
        ),
        'validation fails while running the next command': ValidationErrorDataset(
            fixture_create_error=None,
            fixture_run_error=None,
            fixture_next_run_error=ValidationError(
                'The invalid config was not applied',
            ),
            expected_stderr='Error: The invalid config was not applied\n',
        ),
    })
    def test_main_reports_validation_errors_without_a_traceback(
        self,
        dataset: ValidationErrorDataset,
    ) -> None:
        """Test that a validation error is shown as a plain message on stderr."""

        # Arrange
        next_command = MagicMock()
        next_command.run.return_value = None
        next_command.run.side_effect = dataset.fixture_next_run_error
        command = MagicMock()
        command.run.return_value = next_command
        command.run.side_effect = dataset.fixture_run_error
        stderr = StringIO()

        # Act
        with patch('sys.argv', ['sysconf', 'edit']), \
                patch.object(
                    EditCommand,
                    'create_from_arguments',
                    return_value=command,
                    side_effect=dataset.fixture_create_error,
        ), \
                patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as context:
                main()

        # Assert
        self.assertEqual(context.exception.code, 1)
        self.assertEqual(stderr.getvalue(), dataset.expected_stderr)

    def test_main_propagates_unexpected_errors(self) -> None:
        """Test that a programming error still surfaces as a traceback."""

        # Act & Assert
        with patch('sys.argv', ['sysconf', 'show']), \
                patch.object(
                    ShowCommand,
                    'create_from_arguments',
                    side_effect=RuntimeError('boom'),
        ):
            with self.assertRaises(RuntimeError):
                main()
