# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import PurePath

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.system.context import Context
from sysconf.system.file import FileReader
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.storage.default_paths import (
    DEFAULT_CONFIG_LOCATION_PATH,
    DEFAULT_NEW_CONFIG_PATH,
    DEFAULT_OLD_CONFIG_PATH,
)
from test.system.mock_file import MockFileReader, MockFileWriter
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


class TestComparativeConfigCommandParser(TestCase):

    @dataclass
    class AddArgumentsDataset:
        input_args: list[str]
        expected_config_file: PurePath | None
        expected_last_config: PurePath | None

    @datasets({
        'config file': AddArgumentsDataset(
            input_args=['test.yaml'],
            expected_config_file=PurePath('test.yaml'),
            expected_last_config=None,
        ),
        'last config file': AddArgumentsDataset(
            input_args=['--last-config', 'old.yaml'],
            expected_config_file=None,
            expected_last_config=PurePath('old.yaml'),
        ),
        'both config file and last config': AddArgumentsDataset(
            input_args=['test.yaml', '--last-config', 'old.yaml'],
            expected_config_file=PurePath('test.yaml'),
            expected_last_config=PurePath('old.yaml'),
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
        fixture_path_service: MockPathService
        input_parsed_arguments: Namespace
        expected_old_path: PurePath
        expected_new_path: PurePath
        expected_is_config_file_explicit: bool

    @datasets({
        'both paths provided': CreateFromArgumentsSuccessDataset(
            fixture_path_service=MockPathService(
                files={
                    DEFAULT_NEW_CONFIG_PATH,
                    DEFAULT_OLD_CONFIG_PATH,
                    '/manual/new.yaml',
                    '/manual/old.yaml',
                },
            ),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/new.yaml'),
                last_config=PurePath('/manual/old.yaml'),
            ),
            expected_old_path=PurePath('/manual/old.yaml'),
            expected_new_path=PurePath('/manual/new.yaml'),
            expected_is_config_file_explicit=True,
        ),
        'only new config provided, uses default old path': CreateFromArgumentsSuccessDataset(
            fixture_path_service=MockPathService(
                files={
                    DEFAULT_NEW_CONFIG_PATH,
                    DEFAULT_OLD_CONFIG_PATH,
                    '/manual/new.yaml',
                },
            ),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/new.yaml'),
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath('/manual/new.yaml'),
            expected_is_config_file_explicit=True,
        ),
        'only old config provided, uses the recorded config location': CreateFromArgumentsSuccessDataset(
            fixture_path_service=MockPathService(
                files={
                    DEFAULT_NEW_CONFIG_PATH,
                    DEFAULT_OLD_CONFIG_PATH,
                    '/manual/old.yaml',
                },
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=PurePath('/manual/old.yaml'),
            ),
            expected_old_path=PurePath('/manual/old.yaml'),
            expected_new_path=PurePath(DEFAULT_NEW_CONFIG_PATH),
            expected_is_config_file_explicit=False,
        ),
        'no paths provided, uses the recorded config location': CreateFromArgumentsSuccessDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath(DEFAULT_NEW_CONFIG_PATH),
            expected_is_config_file_explicit=False,
        ),
        'default old path does not exist yet': CreateFromArgumentsSuccessDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=PurePath(DEFAULT_OLD_CONFIG_PATH),
            expected_new_path=PurePath(DEFAULT_NEW_CONFIG_PATH),
            expected_is_config_file_explicit=False,
        ),
    })
    def test_create_from_arguments_success(
        self,
        dataset: CreateFromArgumentsSuccessDataset,
    ) -> None:
        """Test successful creation from arguments with various input combinations."""

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
        fixture_path_service: MockPathService
        input_parsed_arguments: Namespace
        expected_exception_message: str

    @datasets({
        'no config location recorded': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='No config location recorded',
        ),
        'recorded config location holds no config file': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_OLD_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_exception_message='does not exist',
        ),
        'new config param file not found': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=PurePath('nonexistent.yaml'),
                last_config=None
            ),
            expected_exception_message='does not exist',
        ),
        'new config param is directory': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
                dirs={'/manual/directory'},
            ),
            input_parsed_arguments=Namespace(
                config_file=PurePath('/manual/directory'),
                last_config=None
            ),
            expected_exception_message='not a file',
        ),
        'old config param is directory': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH, '/manual/directory'},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=PurePath('/manual/directory'),
            ),
            expected_exception_message='not a file',
        ),
        'old config param file not found': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH, DEFAULT_OLD_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=PurePath('/manual/old.yaml'),
            ),
            expected_exception_message='does not exist',
        ),
        'default old path is directory': CreateFromArgumentsErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_NEW_CONFIG_PATH},
                dirs={DEFAULT_CONFIG_LOCATION_PATH, DEFAULT_OLD_CONFIG_PATH},
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
        file_reader = MockFileReader({})
        file_writer = MockFileWriter()
        system_executor = MockSystemExecutor()
        context = Context(
            file_reader=file_reader,
            file_writer=file_writer,
            path_service=dataset.fixture_path_service,
            system_executor=system_executor,
        )

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
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            expected_equal=True,
        ),
        'different old path': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=PurePath('/other.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            expected_equal=False,
        ),
        'different new path': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/other.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            expected_equal=False,
        ),
        'different config file explicitness': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            input_other=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=False,
                file_reader=FileReader(),
            ),
            expected_equal=False,
        ),
        'not a parser': EqualityDataset(
            input_parser=ComparativeConfigCommandParser(
                old_path=PurePath('/old.yaml'),
                new_path=PurePath('/new.yaml'),
                is_config_file_explicit=True,
                file_reader=FileReader(),
            ),
            input_other='parser',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that parsers compare by paths, explicitness and file reader."""

        # Act
        actual = dataset.input_parser == dataset.input_other

        # Assert
        self.assertEqual(actual, dataset.expected_equal)
