# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.system.file import FileReader
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_context import MockContext
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_path import MockPath, dpath, fpath


FILE_READER = FileReader()


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
        expected_old_path: Path
        expected_new_path: Path
        expected_is_config_file_explicit: bool

    @datasets({
        'both paths provided': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=MockPath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
            expected_is_config_file_explicit=True,
        ),
        'only new config provided, uses default old path': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=MockPath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_old_path=fpath('/default/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
            expected_is_config_file_explicit=True,
        ),
        'only old config provided, uses the recorded config location': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
            expected_is_config_file_explicit=False,
        ),
        'no paths provided, uses the recorded config location': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=fpath('/default/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
            expected_is_config_file_explicit=False,
        ),
        'default old path does not exist yet': CreateFromArgumentsSuccessDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=MockPath('/default/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
            expected_is_config_file_explicit=False,
        ),
    })
    def test_create_from_arguments_success(
        self,
        dataset: CreateFromArgumentsSuccessDataset,
    ) -> None:
        """Test successful creation from arguments with various input combinations."""

        # Arrange
        context = MockContext.create(defaults=dataset.fixture_defaults)
        file_reader = context.get_file_reader()
        expected = ComparativeConfigCommandParser(
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
            is_config_file_explicit=dataset.expected_is_config_file_explicit,
            file_reader=file_reader,
        )

        # Act
        actual = ComparativeConfigCommandParser.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertEqual(expected, actual)

    @dataclass
    class CreateFromArgumentsErrorDataset:
        fixture_defaults: MockDefaults
        input_parsed_arguments: Namespace
        expected_exception_message: str

    @datasets({
        'no config location recorded': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=MockPath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='No config location recorded',
        ),
        'recorded config location holds no config file': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=MockPath(
                    '/config/config/config.yaml',
                    is_file=True,
                    exists=False,
                ),
                config_location_path=dpath('/config/config'),
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
                config_location_path=MockPath('/config/config'),
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
                config_location_path=MockPath('/config/config'),
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
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=dpath('/manual/directory'),
            ),
            expected_exception_message='not a file',
        ),
        'old config param file not found': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=fpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=MockPath('/manual/old.yaml'),
            ),
            expected_exception_message='does not exist',
        ),
        'default old path is directory': CreateFromArgumentsErrorDataset(
            fixture_defaults=MockDefaults(
                old_config_path=dpath('/default/old.yaml'),
                new_config_path=fpath('/default/new.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='not a file',
        ),
    })
    def test_create_from_arguments_error(
        self,
        dataset: CreateFromArgumentsErrorDataset,
    ) -> None:
        """Test that various config loading errors are properly propagated."""

        # Arrange
        context = MockContext.create(defaults=dataset.fixture_defaults)

        # Act & Expect
        with self.assertRaises(ValidationError) as error_context:
            ComparativeConfigCommandParser.create_from_arguments(
                context=context,
                parsed_arguments=dataset.input_parsed_arguments,
            )

        # Assert
        self.assertIn(
            dataset.expected_exception_message,
            str(error_context.exception),
        )

    @dataclass
    class EqualityDataset:
        input_parser: ComparativeConfigCommandParser
        input_other: object
        expected_equal: bool

    @datasets({
        'same paths and reader': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            expected_equal=True,
        ),
        'different old path': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=Path('/other.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            expected_equal=False,
        ),
        'different new path': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/other.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            expected_equal=False,
        ),
        'different config file explicitness': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=False,
                file_reader=FILE_READER,
            ),
            expected_equal=False,
        ),
        'different file reader instance': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            expected_equal=False,
        ),
        'not a parser': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=Path('/old.yaml'),
                new_path=Path('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FILE_READER,
            ),
            input_other='parser',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that parsers compare by paths, explicitness and file reader."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_parser, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_parser, dataset.input_other)
