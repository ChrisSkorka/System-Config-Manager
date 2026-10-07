# pyright: strict

from dataclasses import dataclass
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory
from typing import Sequence, Set

from sysconf.system.path_service import PathService
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.system.mock_path_service import MockPathService
from test.test_case import TestCase


class TestGetValidatedFilePath(TestCase):
    """Test validation of a user supplied file path."""

    @dataclass
    class ValidPathDataset:
        fixture_path_service: MockPathService
        input_path: PurePath
        input_allowed_suffix: Sequence[str] | Set[str] | str | None
        expected_path: PurePath

    @datasets({
        'an existing file without a suffix restriction': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.yaml'},
            ),
            input_path=PurePath('/configs/system.yaml'),
            input_allowed_suffix=None,
            expected_path=PurePath('/configs/system.yaml'),
        ),
        'a suffix given as a plain string': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.yaml'},
            ),
            input_path=PurePath('/configs/system.yaml'),
            input_allowed_suffix='.yaml',
            expected_path=PurePath('/configs/system.yaml'),
        ),
        'a suffix given as a sequence': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.yml'},
            ),
            input_path=PurePath('/configs/system.yml'),
            input_allowed_suffix=('.yaml', '.yml'),
            expected_path=PurePath('/configs/system.yml'),
        ),
        'a suffix given as a set': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.yaml'},
            ),
            input_path=PurePath('/configs/system.yaml'),
            input_allowed_suffix={'.yaml', '.yml'},
            expected_path=PurePath('/configs/system.yaml'),
        ),
        'the home shorthand is expanded': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/home/user/dotfiles/system.yaml'},
                home_dir='/home/user',
            ),
            input_path=PurePath('~/dotfiles/system.yaml'),
            input_allowed_suffix='.yaml',
            expected_path=PurePath('/home/user/dotfiles/system.yaml'),
        ),
        'a relative path is kept relative': ValidPathDataset(
            fixture_path_service=MockPathService(
                files={'/working/system.yaml'},
                working_dir='/working',
            ),
            input_path=PurePath('system.yaml'),
            input_allowed_suffix='.yaml',
            expected_path=PurePath('system.yaml'),
        ),
    })
    def test_get_validated_file_path_accepts_a_valid_file(
        self,
        dataset: ValidPathDataset,
    ) -> None:
        """Test that a valid file path is expanded and returned."""

        # Act
        result = dataset.fixture_path_service.get_validated_file_path(
            dataset.input_path,
            dataset.input_allowed_suffix,
        )

        # Assert
        self.assertEqual(result, dataset.expected_path)

    @dataclass
    class InvalidPathDataset:
        fixture_path_service: MockPathService
        input_path: PurePath
        input_allowed_suffix: Sequence[str] | Set[str] | str | None
        expected_message_contains: str

    @datasets({
        'a path that does not exist': InvalidPathDataset(
            fixture_path_service=MockPathService(),
            input_path=PurePath('/configs/missing.yaml'),
            input_allowed_suffix='.yaml',
            expected_message_contains='/configs/missing.yaml does not exist',
        ),
        'a directory': InvalidPathDataset(
            fixture_path_service=MockPathService(dirs={'/configs'}),
            input_path=PurePath('/configs'),
            input_allowed_suffix=None,
            expected_message_contains='/configs is not a file',
        ),
        'a file with a disallowed suffix': InvalidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.json'},
            ),
            input_path=PurePath('/configs/system.json'),
            input_allowed_suffix='.yaml',
            expected_message_contains='is not a valid file type',
        ),
        'a file with a suffix outside the allowed sequence': InvalidPathDataset(
            fixture_path_service=MockPathService(
                files={'/configs/system.json'},
            ),
            input_path=PurePath('/configs/system.json'),
            input_allowed_suffix=('.yaml', '.yml'),
            expected_message_contains='is not a valid file type',
        ),
    })
    def test_get_validated_file_path_rejects_an_invalid_file(
        self,
        dataset: InvalidPathDataset,
    ) -> None:
        """Test that an invalid path is reported as a configuration error."""

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            dataset.fixture_path_service.get_validated_file_path(
                dataset.input_path,
                dataset.input_allowed_suffix,
            )

        self.assertIn(
            dataset.expected_message_contains,
            str(context.exception),
        )


class TestEndToEndPathService(TestCase):
    """
    Test the PathService against the real file system.

    These tests intentionally touch the file system (inside a temporary
    directory) since the PathService is mocked everywhere else.
    """

    def setUp(self) -> None:
        self._temp_directory = TemporaryDirectory()
        self.base_path = Path(self._temp_directory.name).resolve()
        file_path = self.base_path / 'file.yaml'
        file_path.write_text('', encoding='utf-8')
        (self.base_path / 'directory').mkdir()
        (self.base_path / 'link.yaml').symlink_to(file_path)

    def tearDown(self) -> None:
        self._temp_directory.cleanup()

    @dataclass
    class QueryDataset:
        input_relative_path: str
        expected_exists: bool
        expected_is_file: bool
        expected_is_dir: bool

    @datasets({
        'a file': QueryDataset(
            input_relative_path='file.yaml',
            expected_exists=True,
            expected_is_file=True,
            expected_is_dir=False,
        ),
        'a directory': QueryDataset(
            input_relative_path='directory',
            expected_exists=True,
            expected_is_file=False,
            expected_is_dir=True,
        ),
        'a symlink to a file': QueryDataset(
            input_relative_path='link.yaml',
            expected_exists=True,
            expected_is_file=True,
            expected_is_dir=False,
        ),
        'a missing path': QueryDataset(
            input_relative_path='missing.yaml',
            expected_exists=False,
            expected_is_file=False,
            expected_is_dir=False,
        ),
    })
    def test_queries(self, dataset: QueryDataset) -> None:
        """Test that exists, is_file & is_dir reflect the file system."""

        # Arrange
        path_service = PathService()
        path = PurePath(self.base_path, dataset.input_relative_path)

        # Act
        actual = (
            path_service.exists(path),
            path_service.is_file(path),
            path_service.is_dir(path),
        )

        # Assert
        expected = (
            dataset.expected_exists,
            dataset.expected_is_file,
            dataset.expected_is_dir,
        )
        self.assertEqual(actual, expected)

    def test_expand_user(self) -> None:
        """Test that the home shorthand is expanded to a plain PurePath."""

        # Arrange
        path_service = PathService()
        path = PurePath('~/dotfiles/system.yaml')

        # Act
        actual = path_service.expand_user(path)

        # Assert
        self.assertEqual(actual, Path.home() / 'dotfiles/system.yaml')
        self.assertNotIsInstance(actual, Path)

    def test_resolve(self) -> None:
        """Test that `..` & symlinks are resolved to a plain PurePath."""

        # Arrange
        path_service = PathService()
        path = PurePath(self.base_path, 'directory', '..', 'link.yaml')

        # Act
        actual = path_service.resolve(path)

        # Assert
        self.assertEqual(actual, self.base_path / 'file.yaml')
        self.assertNotIsInstance(actual, Path)

    def test_make_dirs(self) -> None:
        """Test that nested directories are created, existing ones are kept."""

        # Arrange
        path_service = PathService()
        path = PurePath(self.base_path, 'a', 'b')
        path_service.make_dirs(path)

        # Act
        path_service.make_dirs(path)

        # Assert
        self.assertTrue(Path(path).is_dir())
