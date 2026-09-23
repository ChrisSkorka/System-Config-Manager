# pyright: strict

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Set

from sysconf.system.path import get_validated_file_path
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_path import MockPath, dpath, fpath


class TestGetValidatedFilePath(TestCase):
    """Test validation of a user supplied file path."""

    @dataclass
    class ValidPathDataset:
        input_path: MockPath
        input_allowed_suffix: Sequence[str] | Set[str] | str | None
        expected_path: Path

    @datasets({
        'an existing file without a suffix restriction': ValidPathDataset(
            input_path=fpath('/configs/system.yaml'),
            input_allowed_suffix=None,
            expected_path=Path('/configs/system.yaml'),
        ),
        'a suffix given as a plain string': ValidPathDataset(
            input_path=fpath('/configs/system.yaml'),
            input_allowed_suffix='.yaml',
            expected_path=Path('/configs/system.yaml'),
        ),
        'a suffix given as a sequence': ValidPathDataset(
            input_path=fpath('/configs/system.yml'),
            input_allowed_suffix=('.yaml', '.yml'),
            expected_path=Path('/configs/system.yml'),
        ),
        'a suffix given as a set': ValidPathDataset(
            input_path=fpath('/configs/system.yaml'),
            input_allowed_suffix={'.yaml', '.yml'},
            expected_path=Path('/configs/system.yaml'),
        ),
        'the home shorthand is expanded': ValidPathDataset(
            input_path=MockPath(
                '~/dotfiles/system.yaml',
                is_file=True,
                exists=True,
                expanded_path='/home/user/dotfiles/system.yaml',
            ),
            input_allowed_suffix='.yaml',
            expected_path=Path('/home/user/dotfiles/system.yaml'),
        ),
    })
    def test_get_validated_file_path_accepts_a_valid_file(
        self,
        dataset: ValidPathDataset,
    ) -> None:
        """Test that a valid file path is expanded and returned."""

        # Act
        result = get_validated_file_path(
            dataset.input_path,
            dataset.input_allowed_suffix,
        )

        # Assert
        self.assertEqual(result, dataset.expected_path)

    @dataclass
    class InvalidPathDataset:
        input_path: MockPath
        input_allowed_suffix: Sequence[str] | Set[str] | str | None
        expected_message_contains: str

    @datasets({
        'a path that does not exist': InvalidPathDataset(
            input_path=MockPath(
                '/configs/missing.yaml',
                is_file=True,
                exists=False,
            ),
            input_allowed_suffix='.yaml',
            expected_message_contains='/configs/missing.yaml does not exist',
        ),
        'a directory': InvalidPathDataset(
            input_path=dpath('/configs'),
            input_allowed_suffix=None,
            expected_message_contains='/configs is not a file',
        ),
        'a file with a disallowed suffix': InvalidPathDataset(
            input_path=fpath('/configs/system.json'),
            input_allowed_suffix='.yaml',
            expected_message_contains='is not a valid file type',
        ),
        'a file with a suffix outside the allowed sequence': InvalidPathDataset(
            input_path=fpath('/configs/system.json'),
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
            get_validated_file_path(
                dataset.input_path,
                dataset.input_allowed_suffix,
            )

        self.assertIn(
            dataset.expected_message_contains,
            str(context.exception),
        )
