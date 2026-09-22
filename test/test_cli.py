# pyright: strict

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Type
from unittest.mock import MagicMock, patch

from sysconf.cli import main
from sysconf.commands.apply_command import ApplyCommand
from sysconf.commands.command import Command
from sysconf.commands.preview_command import PreviewCommand
from sysconf.commands.show_command import ShowCommand
from test.datasets import datasets
from test.test_case import TestCase


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
                config_path=Path('~/.config/system.config.yaml'),
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
    })
    def test_main_runs_the_selected_command(self, dataset: MainDataset) -> None:
        """Test that the sub command is parsed, constructed and run."""

        # Arrange
        mock_command = MagicMock()

        # Act
        with patch('sys.argv', dataset.input_argv), \
                patch.object(
                    dataset.fixture_command_class,
                    'create_from_arguments',
                    return_value=mock_command,
                ) as mock_create_from_arguments:
            main()

        # Assert
        mock_create_from_arguments.assert_called_once_with(
            dataset.expected_parsed_arguments,
        )
        mock_command.run.assert_called_once_with()

    def test_main_without_a_command_prints_help(self) -> None:
        """Test that invoking the cli with no sub command prints the help."""

        # Act
        with patch('sys.argv', ['sysconf']), \
                patch('argparse.ArgumentParser.print_help') as mock_print_help, \
                patch.object(ShowCommand, 'create_from_arguments') as mock_show, \
                patch.object(PreviewCommand, 'create_from_arguments') as mock_preview, \
                patch.object(ApplyCommand, 'create_from_arguments') as mock_apply:
            main()

        # Assert
        mock_print_help.assert_called_once_with()
        for mock_create in (mock_show, mock_preview, mock_apply):
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
