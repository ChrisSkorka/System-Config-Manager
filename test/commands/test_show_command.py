# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from sysconf.commands.show_command import ShowCommand
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_path import MockPath, fpath


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
        self.assertIsInstance(actual, ArgumentParser)

        help_text = actual.format_help()
        self.assertIn('Shows the last applied System Configuration', help_text)

    @dataclass
    class AddArgumentsDataset:
        input_argv: list[str]
        expected_config_path: Path

    @datasets({
        'explicit path provided': AddArgumentsDataset(
            input_argv=['/manual/config.yaml'],
            expected_config_path=Path('/manual/config.yaml'),
        ),
        'no path uses default': AddArgumentsDataset(
            input_argv=[],
            expected_config_path=Path('~/.config/system.config.yaml'),
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
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_config_path: MockPath

    @datasets({
        'explicit path provided': CreateFromArgumentsDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/default/old.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_path=fpath('/manual/config.yaml'),
            ),
            expected_config_path=fpath('/manual/config.yaml'),
        ),
        'no path falls back to default': CreateFromArgumentsDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_path=None,
            ),
            expected_config_path=fpath('/default/old.yaml'),
        ),
    })
    @patch('sysconf.commands.show_command.get_validated_file_path')
    @patch('sysconf.commands.show_command.Defaults')
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
        mock_defaults_class: MagicMock,
        mock_get_validated_file_path: MagicMock,
    ) -> None:
        """Test creation from arguments, falling back to the default path."""

        # Arrange
        mock_defaults_class.return_value = dataset.fixture_defaults

        def return_path(path: Path, _suffix: str) -> Path:
            return path

        mock_get_validated_file_path.side_effect = return_path

        # Act
        actual = ShowCommand.create_from_arguments(
            dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIsInstance(actual, ShowCommand)
        self.assertEqual(actual.config_path, dataset.expected_config_path)
        mock_get_validated_file_path.assert_called_once_with(
            dataset.expected_config_path,
            '.yaml',
        )

    def test_run(self) -> None:
        """Test that run prints the header and the loaded configuration."""

        # Arrange
        config_path = fpath('/config/current.yaml')
        loaded_config = MagicMock()
        show_command = ShowCommand(config_path=config_path)

        # Act
        with patch(
            'sysconf.commands.show_command.load_config_from_file',
            return_value=loaded_config,
        ) as mock_load_config, patch('builtins.print') as mock_print:
            show_command.run()

        # Assert
        mock_load_config.assert_called_once_with(
            show_command.file_reader,
            config_path,
        )
        mock_print.assert_has_calls(
            [
                call('Listing current system configuration...'),
                call(loaded_config),
            ],
            any_order=False,
        )
