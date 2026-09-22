# pyright: strict

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from sysconf.system.file import FileReader, FileWriter
from test.datasets import datasets
from test.helper import unindent
from test.test_case import TestCase


@dataclass
class FileDataset:
    """A file path (relative to the temporary directory) and its contents."""

    input_relative_path: str
    input_contents: str


FILE_DATASETS: dict[str, FileDataset] = {
    'single line': FileDataset(
        input_relative_path='config.yaml',
        input_contents='version: 1',
    ),
    'empty file': FileDataset(
        input_relative_path='empty.yaml',
        input_contents='',
    ),
    'multiline yaml': FileDataset(
        input_relative_path='system.yaml',
        input_contents=unindent("""
            version: 1
            config:
              - gsettings:
                  org.schema:
                    key: value
        """),
    ),
    'trailing newline is preserved': FileDataset(
        input_relative_path='trailing.yaml',
        input_contents='version: 1\n',
    ),
    'non ascii characters': FileDataset(
        input_relative_path='unicode.yaml',
        input_contents='name: Ünicode — ✓ 日本語',
    ),
}


class EndToEndFileTestCase(TestCase):
    """
    Base for tests that exercise the real file system.

    These tests intentionally touch the file system (inside a temporary
    directory) since FileReader/FileWriter are mocked everywhere else.
    """

    def setUp(self) -> None:
        self._temp_directory = TemporaryDirectory()
        self.base_path = Path(self._temp_directory.name)

    def tearDown(self) -> None:
        self._temp_directory.cleanup()


class TestEndToEndFileWriter(EndToEndFileTestCase):
    """Test that FileWriter writes real files."""

    @datasets({
        **FILE_DATASETS,
        'nested directories are created': FileDataset(
            input_relative_path='.history/nested/current.yaml',
            input_contents='version: 1',
        ),
    })
    def test_write_file_contents(self, dataset: FileDataset) -> None:
        """Test that the contents land on disk byte for byte."""

        # Arrange
        path = self.base_path / dataset.input_relative_path
        writer = FileWriter()

        # Act
        writer.write_file_contents(path, dataset.input_contents)

        # Assert
        self.assertTrue(path.is_file())
        self.assertEqual(
            path.read_text(encoding='utf-8'),
            dataset.input_contents,
        )

    def test_write_file_contents_overwrites_an_existing_file(self) -> None:
        """Test that writing to an existing file replaces its contents."""

        # Arrange
        path = self.base_path / 'current.yaml'
        writer = FileWriter()
        writer.write_file_contents(path, 'version: 1\nconfig: []')

        # Act
        writer.write_file_contents(path, 'version: 1')

        # Assert
        self.assertEqual(path.read_text(encoding='utf-8'), 'version: 1')

    def test_write_file_contents_rejects_a_directory_path(self) -> None:
        """Test that writing over an existing directory raises an AssertionError."""

        # Arrange
        path = self.base_path / 'a-directory'
        path.mkdir()
        writer = FileWriter()

        # Act & Assert
        with self.assertRaises(AssertionError) as context:
            writer.write_file_contents(path, 'version: 1')

        self.assertIn('File path is not a file', str(context.exception))


class TestEndToEndFileReader(EndToEndFileTestCase):
    """Test that FileReader reads real files."""

    @datasets(FILE_DATASETS)
    def test_get_file_contents(self, dataset: FileDataset) -> None:
        """Test that the contents are read back byte for byte."""

        # Arrange
        path = self.base_path / dataset.input_relative_path
        path.write_text(dataset.input_contents, encoding='utf-8')
        reader = FileReader()

        # Act
        actual = reader.get_file_contents(path)

        # Assert
        self.assertEqual(actual, dataset.input_contents)

    def test_get_file_contents_of_a_missing_file_raises(self) -> None:
        """Test that reading a file that does not exist raises."""

        # Arrange
        path = self.base_path / 'does-not-exist.yaml'
        reader = FileReader()

        # Act & Assert
        with self.assertRaises(FileNotFoundError):
            reader.get_file_contents(path)
