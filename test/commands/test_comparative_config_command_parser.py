# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch, MagicMock

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.domains.gsettings import GSettingsConfig
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_path import MockPath, dpath, fpath


class TestComparativeConfigCommandParser(TestCase):

    @dataclass
    class AddArgumentsDataset:
        input_args: list[str]
        expected_config_file: Path | None
        expected_last_config: Path | None

    @datasets({
        'config file': AddArgumentsDataset(
            input_args=['test.yaml'],
            expected_config_file=Path('test.yaml'),
            expected_last_config=None,
        ),
        'last config file': AddArgumentsDataset(
            input_args=['--last-config', 'old.yaml'],
            expected_config_file=None,
            expected_last_config=Path('old.yaml'),
        ),
        'both config file and last config': AddArgumentsDataset(
            input_args=['test.yaml', '--last-config', 'old.yaml'],
            expected_config_file=Path('test.yaml'),
            expected_last_config=Path('old.yaml'),
        ),
        'no arguments': AddArgumentsDataset(
            input_args=[],
            expected_config_file=None,
            expected_last_config=None,
        ),
    })
    def test_add_arguments(self, dataset: AddArgumentsDataset) -> None:
        """
        Test that add_arguments correctly adds the expected arguments to the
        parser.
        """

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = ComparativeConfigCommandParser.add_arguments(parser)

        # Assert
        args = parser.parse_args(dataset.input_args)

        self.assertIs(result_parser, parser)
        self.assertEqual(args.config_file, dataset.expected_config_file)
        self.assertEqual(args.last_config, dataset.expected_last_config)

    @dataclass
    class CreateFromArgumentsSuccessDataset:
        fixture_configs: dict[Path, SystemConfig]
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_parser: ComparativeConfigCommandParser

    fixture_configs = {
        Path('/manual/old.yaml'):
        SystemConfig({
            'domain1': GSettingsConfig({('schema', 'key'): 'value1'}),
        }),
        Path('/manual/new.yaml'):
        SystemConfig({
            'domain1': GSettingsConfig({('schema', 'key'): 'value1'}),
            'domain2': GSettingsConfig({('schema', 'key'): 'value2'}),
        }),
        Path('/default/old.yaml'):
        SystemConfig({
            'domain1': GSettingsConfig({('schema', 'key'): 'old'}),
        }),
        Path('/default/new.yaml'):
        SystemConfig({
            'domain2': GSettingsConfig({('schema', 'key'): 'new'}),
        }),
    }

    @datasets({
        'both paths provided': CreateFromArgumentsSuccessDataset(
            fixture_configs=fixture_configs,
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_parser=ComparativeConfigCommandParser(
                SystemManager(
                    old_config=fixture_configs[fpath('/manual/old.yaml')],
                    new_config=fixture_configs[fpath('/manual/new.yaml')],
                )
            ),
        ),
        'only new config provided, uses default old path': CreateFromArgumentsSuccessDataset(
            fixture_configs=fixture_configs,
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=None
            ),
            expected_parser=ComparativeConfigCommandParser(
                SystemManager(
                    old_config=fixture_configs[fpath('/default/old.yaml')],
                    new_config=fixture_configs[fpath('/manual/new.yaml')],
                )
            ),
        ),
        'only old config provided, uses default new path': CreateFromArgumentsSuccessDataset(
            fixture_configs=fixture_configs,
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_parser=ComparativeConfigCommandParser(
                SystemManager(
                    old_config=fixture_configs[fpath('/manual/old.yaml')],
                    new_config=fixture_configs[fpath('/default/new.yaml')],
                )
            ),
        ),
        'no paths provided, uses defaults': CreateFromArgumentsSuccessDataset(
            fixture_configs=fixture_configs,
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None
            ),
            expected_parser=ComparativeConfigCommandParser(
                SystemManager(
                    old_config=fixture_configs[fpath('/default/old.yaml')],
                    new_config=fixture_configs[fpath('/default/new.yaml')],
                ),
            ),
        ),
    })
    @patch('sysconf.commands.comparative_config_command_parser.load_config_from_file')
    @patch('sysconf.commands.comparative_config_command_parser.Defaults')
    def test_create_from_arguments_success(
        self,
        dataset: CreateFromArgumentsSuccessDataset,
        mock_defaults_class: MagicMock,
        mock_load_config_from_file: MagicMock,
    ) -> None:
        """Test successful creation from arguments with various input combinations."""

        # Arrange
        mock_defaults_class.return_value = dataset.fixture_defaults

        def mock_load_config_side_effect(file_reader: object, path: Path) -> SystemConfig:
            # Find the matching MockPath in fixture_configs by comparing the path string
            config = dataset.fixture_configs.get(path)
            if config is not None:
                return config
            raise FileNotFoundError(f"No config found for path {path}")

        mock_load_config_from_file.side_effect = mock_load_config_side_effect

        # Act
        actual = ComparativeConfigCommandParser.create_from_arguments(
            dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIsInstance(actual, ComparativeConfigCommandParser)
        self.assertEqual(actual, dataset.expected_parser)

    @dataclass
    class CreateFromArgumentsErrorDataset:
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_exception_message: str

    @datasets({
        'old default config file not found': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath(
                    '/default/old.yaml',
                    is_file=True,
                    exists=False,
                ),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='does not exist',
        ),
        'new default config file not found': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=MockPath(
                    '/default/new.yaml',
                    is_file=True,
                    exists=False,
                ),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='does not exist',
        ),
        'new config param file not found': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=MockPath(
                    'nonexistent.yaml',
                    is_file=True,
                    exists=False,
                ),
                last_config=None
            ),
            expected_exception_message='does not exist',
        ),
        'old config param file not found': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('test.yaml'),
                last_config=MockPath(
                    'nonexistent.yaml',
                    is_file=True,
                    exists=False,
                ),
            ),
            expected_exception_message='does not exist',
        ),
        'new config param is directory': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=dpath('/manual/directory'),
                last_config=None
            ),
            expected_exception_message='not a file',
        ),
        'old config param is directory': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=dpath('/manual/directory'),
            ),
            expected_exception_message='not a file',
        ),
    })
    @patch('sysconf.commands.comparative_config_command_parser.Defaults')
    def test_create_from_arguments_error(
        self,
        dataset: CreateFromArgumentsErrorDataset,
        mock_defaults_class: MagicMock,
    ) -> None:
        """Test that various config loading errors are properly propagated."""

        # Arrange
        mock_defaults_class.return_value = dataset.fixture_defaults

        # Act & Expect
        with self.assertRaises(Exception) as context:
            ComparativeConfigCommandParser.create_from_arguments(
                dataset.input_parsed_arguments)

        # Assert
        self.assertIn(dataset.expected_exception_message,
                      str(context.exception))

    def test_get_system_manager(self) -> None:
        """Test that get_system_manager returns the correct system manager."""

        # Arrange
        old_config = SystemConfig({'domain1': GSettingsConfig({})})
        new_config = SystemConfig({'domain2': GSettingsConfig({})})
        system_manager = SystemManager(old_config, new_config)
        parser = ComparativeConfigCommandParser(system_manager=system_manager)

        # Act
        result = parser.get_system_manager()

        # Assert
        self.assertIs(result, system_manager)
