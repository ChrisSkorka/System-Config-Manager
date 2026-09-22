# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from sysconf.commands.preview_command import PreviewCommand
from test.commands.mock_comparative_config_command_parser import MockComparativeConfigCommandParser
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.system.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.utils.mock_path import MockPath, fpath


class TestPreviewCommand(TestCase):

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = PreviewCommand.get_name()

        # Assert
        self.assertIsInstance(result, str)

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = PreviewCommand.get_subparser(subparsers)

        # Assert
        self.assertIsInstance(actual, ArgumentParser)

        help_text = actual.format_help()
        self.assertIn('Preview', help_text)

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
        actual = PreviewCommand.create_from_arguments(
            dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIsInstance(actual, PreviewCommand)
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
        preview_command = PreviewCommand(
            manager=dataset.fixture_system_manager,
            system_config_renderer=MagicMock(),
            yaml_serializer=MagicMock(),
            current_path=MockPath('/tmp/current.yaml', is_file=False, exists=False),
            file_writer=MagicMock(),
        )

        # Act
        with patch('builtins.print') as mock_print:
            preview_command.run()

        # Assert
        mock_print.assert_has_calls(
            [call(p) for p in dataset.expected_prints],
            any_order=False,
        )
