# pyright: strict

from dataclasses import dataclass
from pathlib import Path

from sysconf.utils.validation import ValidationError
from sysconf.utils.config_location import ConfigLocationReader, ConfigLocationWriter
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter
from test.utils.mock_path import MockPath, dpath, fpath


class TestConfigLocationReader(TestCase):
    """Test resolving where the source of truth configuration lives."""

    @dataclass
    class GetConfigPathDataset:
        fixture_defaults: MockDefaults
        fixture_file_reader: MockFileReader
        expected_path: Path

    @datasets({
        'recorded location is a directory': GetConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=dpath('/config/config'),
                new_config_path=MockPath('/config/config/config.yaml'),
            ),
            fixture_file_reader=MockFileReader({}),
            expected_path=Path('/config/config/config.yaml'),
        ),
        'recorded location is a file': GetConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '/dotfiles/system.yaml',
            }),
            expected_path=Path('/dotfiles/system.yaml'),
        ),
        'recorded location has surrounding whitespace': GetConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '\n  /dotfiles/system.yaml  \n',
            }),
            expected_path=Path('/dotfiles/system.yaml'),
        ),
        'recorded location uses the home shorthand': GetConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '~/dotfiles/system.yaml',
            }),
            expected_path=Path('~/dotfiles/system.yaml').expanduser(),
        ),
    })
    def test_get_config_path(self, dataset: GetConfigPathDataset) -> None:
        """Test that the configuration path is resolved for each location form."""

        # Arrange
        reader = ConfigLocationReader(
            dataset.fixture_defaults,
            dataset.fixture_file_reader,
        )

        # Act
        actual = reader.get_config_path()

        # Assert
        self.assertEqual(actual, dataset.expected_path)

    @dataclass
    class GetConfigPathErrorDataset:
        fixture_defaults: MockDefaults
        fixture_file_reader: MockFileReader
        expected_message_contains: str

    @datasets({
        'nothing recorded': GetConfigPathErrorDataset(
            fixture_defaults=MockDefaults(
                config_location_path=MockPath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            expected_message_contains='No config location recorded',
        ),
        'recorded location is empty': GetConfigPathErrorDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '',
            }),
            expected_message_contains='is empty',
        ),
        'recorded location is blank': GetConfigPathErrorDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '  \n  ',
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
        reader = ConfigLocationReader(
            dataset.fixture_defaults,
            dataset.fixture_file_reader,
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
        fixture_defaults: MockDefaults
        fixture_file_reader: MockFileReader
        input_argument_path: Path
        expected_recorded: bool
        expected_written_files: dict[str, str]

    @datasets({
        'recorded location is a directory': RecordConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=dpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            input_argument_path=fpath('/manual/new.yaml'),
            expected_recorded=False,
            expected_written_files={},
        ),
        'nothing recorded yet': RecordConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=MockPath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({}),
            input_argument_path=fpath('/manual/new.yaml'),
            expected_recorded=True,
            expected_written_files={
                '/config/config': '/manual/new.yaml\n',
            },
        ),
        'a different location is recorded': RecordConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '/other/old.yaml\n',
            }),
            input_argument_path=fpath('/manual/new.yaml'),
            expected_recorded=True,
            expected_written_files={
                '/config/config': '/manual/new.yaml\n',
            },
        ),
        'this location is already recorded': RecordConfigPathDataset(
            fixture_defaults=MockDefaults(
                config_location_path=fpath('/config/config'),
            ),
            fixture_file_reader=MockFileReader({
                '/config/config': '/manual/new.yaml\n',
            }),
            input_argument_path=fpath('/manual/new.yaml'),
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
        writer = ConfigLocationWriter(
            dataset.fixture_defaults,
            dataset.fixture_file_reader,
            file_writer,
        )

        # Act
        actual = writer.record_config_path(dataset.input_argument_path)

        # Assert
        self.assertEqual(actual, dataset.expected_recorded)
        self.assertEqual(file_writer.written_files,
                         dataset.expected_written_files)
