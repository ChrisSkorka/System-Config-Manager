# pyright: strict

from dataclasses import dataclass
from pathlib import PurePath

from sysconf.utils.validation import ValidationError
from sysconf.utils.config_location import ConfigLocationReader, ConfigLocationWriter
from sysconf.utils.defaults import Defaults
from test.datasets import datasets
from test.system.mock_path_service import MockPathService
from test.test_case import TestCase
from test.utils.default_paths import (
    DEFAULT_CONFIG_LOCATION_PATH,
    DEFAULT_NEW_CONFIG_PATH,
)
from test.utils.mock_file import MockFileReader, MockFileWriter


class TestConfigLocationReader(TestCase):
    """Test resolving where the source of truth configuration lives."""

    @dataclass
    class GetConfigPathDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        expected_path: PurePath

    @datasets({
        'recorded location is a directory': GetConfigPathDataset(
            fixture_path_service=MockPathService(
                dirs={DEFAULT_CONFIG_LOCATION_PATH}),
            fixture_file_reader=MockFileReader({}),
            expected_path=PurePath(DEFAULT_NEW_CONFIG_PATH),
        ),
        'recorded location is a file': GetConfigPathDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH}),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '/dotfiles/system.yaml',
            }),
            expected_path=PurePath('/dotfiles/system.yaml'),
        ),
        'recorded location has surrounding whitespace': GetConfigPathDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '\n  /dotfiles/system.yaml  \n',
            }),
            expected_path=PurePath('/dotfiles/system.yaml'),
        ),
        'recorded location uses the home shorthand': GetConfigPathDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
                home_dir='/home/user',
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '~/dotfiles/system.yaml',
            }),
            expected_path=PurePath('/home/user/dotfiles/system.yaml'),
        ),
    })
    def test_get_config_path(self, dataset: GetConfigPathDataset) -> None:
        """Test that the configuration path is resolved for each location form."""

        # Arrange
        defaults = Defaults(dataset.fixture_path_service)
        reader = ConfigLocationReader(
            defaults,
            dataset.fixture_file_reader,
            dataset.fixture_path_service,
        )

        # Act
        actual = reader.get_config_path()

        # Assert
        self.assertEqual(actual, dataset.expected_path)

    @dataclass
    class GetConfigPathErrorDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        expected_message_contains: str

    @datasets({
        'nothing recorded': GetConfigPathErrorDataset(
            fixture_path_service=MockPathService(),
            fixture_file_reader=MockFileReader({}),
            expected_message_contains='No config location recorded',
        ),
        'recorded location is empty': GetConfigPathErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '',
            }),
            expected_message_contains='is empty',
        ),
        'recorded location is blank': GetConfigPathErrorDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '  \n  ',
            }),
            expected_message_contains='is empty',
        ),
    })
    def test_get_config_path_raises(
        self,
        dataset: GetConfigPathErrorDataset,
    ) -> None:
        """Test that an unusable config location is reported to the user."""

        # Arrange
        defaults = Defaults(dataset.fixture_path_service)
        reader = ConfigLocationReader(
            defaults,
            dataset.fixture_file_reader,
            dataset.fixture_path_service,
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            reader.get_config_path()

        self.assertIn(
            dataset.expected_message_contains,
            str(context.exception),
        )


class TestConfigLocationWriter(TestCase):
    """Test recording where the source of truth configuration lives."""

    @dataclass
    class RecordConfigPathDataset:
        fixture_path_service: MockPathService
        fixture_file_reader: MockFileReader
        input_argument_path: PurePath
        expected_recorded: bool
        expected_written_files: dict[str, str]

    @datasets({
        'recorded location is a directory': RecordConfigPathDataset(
            fixture_path_service=MockPathService(
                dirs={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({}),
            input_argument_path=PurePath('/manual/new.yaml'),
            expected_recorded=False,
            expected_written_files={},
        ),
        'nothing recorded yet': RecordConfigPathDataset(
            fixture_path_service=MockPathService(),
            fixture_file_reader=MockFileReader({}),
            input_argument_path=PurePath('/manual/new.yaml'),
            expected_recorded=True,
            expected_written_files={
                DEFAULT_CONFIG_LOCATION_PATH: '/manual/new.yaml\n',
            },
        ),
        'a different location is recorded': RecordConfigPathDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '/other/old.yaml\n',
            }),
            input_argument_path=PurePath('/manual/new.yaml'),
            expected_recorded=True,
            expected_written_files={
                DEFAULT_CONFIG_LOCATION_PATH: '/manual/new.yaml\n',
            },
        ),
        'this location is already recorded': RecordConfigPathDataset(
            fixture_path_service=MockPathService(
                files={DEFAULT_CONFIG_LOCATION_PATH},
            ),
            fixture_file_reader=MockFileReader({
                DEFAULT_CONFIG_LOCATION_PATH: '/manual/new.yaml\n',
            }),
            input_argument_path=PurePath('/manual/new.yaml'),
            expected_recorded=False,
            expected_written_files={},
        ),
    })
    def test_record_config_path(
        self,
        dataset: RecordConfigPathDataset,
    ) -> None:
        """Test what gets recorded for each config location form."""

        # Arrange
        file_writer = MockFileWriter()
        defaults = Defaults(dataset.fixture_path_service)
        writer = ConfigLocationWriter(
            defaults,
            dataset.fixture_file_reader,
            file_writer,
            dataset.fixture_path_service,
        )

        # Act
        actual = writer.record_config_path(dataset.input_argument_path)

        # Assert
        self.assertEqual(actual, dataset.expected_recorded)
        self.assertEqual(file_writer.written_files,
                         dataset.expected_written_files)
