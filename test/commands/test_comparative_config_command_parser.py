# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch, MagicMock

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.file import FileReader
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
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_old_path: Path | None
        expected_new_path: Path

    @datasets({
        'both paths provided': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
        ),
        'only new config provided, uses default old path': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_old_path=fpath('/default/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
        ),
        'only old config provided, uses default new path': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
        ),
        'no paths provided, uses defaults': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=fpath('/default/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
        ),
    })
    @patch('sysconf.commands.comparative_config_command_parser.Defaults')
    def test_create_from_arguments_success(
        self,
        dataset: CreateFromArgumentsSuccessDataset,
        mock_defaults_class: MagicMock,
    ) -> None:
        """Test successful creation from arguments with various input combinations."""

        # Arrange
        mock_defaults_class.return_value = dataset.fixture_defaults

        # Act
        actual = ComparativeConfigCommandParser.create_from_arguments(
            dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIsInstance(actual, ComparativeConfigCommandParser)
        self.assertEqual(actual.old_path, dataset.expected_old_path)
        self.assertEqual(actual.new_path, dataset.expected_new_path)
        self.assertIsInstance(actual.file_reader, FileReader)

    @dataclass
    class CreateFromArgumentsErrorDataset:
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_exception_message: str

    @datasets({
        # Note: missing old config (default or argument) is silently treated as
        # "no previous config" rather than an error — see the # todo comment in
        # ComparativeConfigCommandParser.create_from_arguments.
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
        """Test that get_system_manager loads configs and creates a SystemManager."""

        # Arrange
        from unittest.mock import patch as _patch
        from test.system.mock_system_executor import MockSystemExecutor

        old_config = SystemConfig.create_from_entries((), (), (), ())
        new_config = SystemConfig.create_from_entries((), (), (), ())
        mock_executor = MockSystemExecutor()
        mock_error_handler: MagicMock = MagicMock()

        parser = ComparativeConfigCommandParser(
            old_path=fpath('/old.yaml'),
            new_path=fpath('/new.yaml'),
            file_reader=FileReader(),
        )

        def mock_load_side_effect(file_reader: object, path: Path) -> SystemConfig:
            return old_config if path == fpath('/old.yaml') else new_config

        with _patch(
            'sysconf.commands.comparative_config_command_parser.load_config_from_file',
            side_effect=mock_load_side_effect,
        ):
            # Act
            result = parser.get_system_manager(
                executor=mock_executor,
                error_handler=mock_error_handler,
            )

        # Assert
        self.assertIsInstance(result, SystemManager)
        self.assertEqual(result.old_config, old_config)
        self.assertEqual(result.new_config, new_config)
