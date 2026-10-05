# pyright: strict

import subprocess

from dataclasses import dataclass
from pathlib import Path

from sysconf.system.editor import EditResult, EditorLauncher, EditorResolver
from sysconf.system.executor import CommandException
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.system.mock_editor import MockWhich
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


class TestEditorResolver(TestCase):
    """Test that the editor command line is found for each platform."""

    @dataclass
    class ResolveDataset:
        input_platform: str
        fixture_paths_by_name: dict[str, str]
        expected: tuple[str, ...]

    @datasets({
        'linux prefers the editor alternative': ResolveDataset(
            input_platform='linux',
            fixture_paths_by_name={
                'editor': '/usr/bin/editor',
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/editor',),
        ),
        'linux without the editor alternative uses nano': ResolveDataset(
            input_platform='linux',
            fixture_paths_by_name={
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/nano',),
        ),
        'linux falls back to vi': ResolveDataset(
            input_platform='linux',
            fixture_paths_by_name={'vi': '/bin/vi'},
            expected=('/bin/vi',),
        ),
        'other posix platforms use the linux chain': ResolveDataset(
            input_platform='freebsd14',
            fixture_paths_by_name={'vim': '/usr/local/bin/vim'},
            expected=('/usr/local/bin/vim',),
        ),
        'macos skips the editor alternative': ResolveDataset(
            input_platform='darwin',
            fixture_paths_by_name={
                'editor': '/usr/local/bin/editor',
                'vim': '/usr/bin/vim',
            },
            expected=('/usr/bin/vim',),
        ),
        'macos prefers nano': ResolveDataset(
            input_platform='darwin',
            fixture_paths_by_name={
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/nano',),
        ),
        'windows uses notepad': ResolveDataset(
            input_platform='win32',
            fixture_paths_by_name={
                'vim': r'C:\Program Files\Git\usr\bin\vim.exe',
                'notepad': r'C:\Windows\system32\notepad.exe',
            },
            expected=(r'C:\Windows\system32\notepad.exe',),
        ),
    })
    def test_get_editor_command_returns(self, dataset: ResolveDataset) -> None:
        """Test that the first installed fallback editor is resolved."""

        # Arrange
        resolver = EditorResolver(
            platform=dataset.input_platform,
            which=MockWhich(dataset.fixture_paths_by_name),
        )

        # Act
        actual = resolver.get_editor_command()

        # Assert
        self.assertEqual(actual, dataset.expected)

    @dataclass
    class ErrorDataset:
        input_platform: str
        fixture_paths_by_name: dict[str, str]
        expected_message: str

    @datasets({
        'no fallback editor is installed on linux': ErrorDataset(
            input_platform='linux',
            fixture_paths_by_name={'notepad': '/usr/bin/notepad'},
            expected_message="No editor found (tried editor, nano, vim, vi)",
        ),
        'no fallback editor is installed on windows': ErrorDataset(
            input_platform='win32',
            fixture_paths_by_name={'vim': r'C:\vim.exe'},
            expected_message="No editor found (tried notepad)",
        ),
    })
    def test_get_editor_command_raises(self, dataset: ErrorDataset) -> None:
        """Test that a missing editor is a validation error."""

        # Arrange
        resolver = EditorResolver(
            platform=dataset.input_platform,
            which=MockWhich(dataset.fixture_paths_by_name),
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            resolver.get_editor_command()

        self.assertEqual(str(context.exception), dataset.expected_message)


class TestEditorLauncher(TestCase):
    """Test launching an editor on a config and reporting what happened."""

    @dataclass
    class EditDataset:
        fixture_editor_exception: Exception | None
        expected: EditResult

    @datasets({
        'editor exits': EditDataset(
            fixture_editor_exception=None,
            expected=EditResult.CLOSED,
        ),
        'editor exits with an error': EditDataset(
            fixture_editor_exception=CommandException(
                'code --wait /configs/config.yaml',
                subprocess.CompletedProcess[bytes](args=[], returncode=1),
            ),
            expected=EditResult.CANCELLED,
        ),
    })
    def test_edit(self, dataset: EditDataset) -> None:
        """Test that the editor runs on the config and the outcome is reported."""

        # Arrange
        executor = MockSystemExecutor()
        executor.command_mock.side_effect = dataset.fixture_editor_exception
        launcher = EditorLauncher(executor)

        # Act
        actual = launcher.edit(
            ('/usr/bin/code', '--wait'),
            Path('/configs/config.yaml'),
        )

        # Assert
        self.assertEqual(actual, dataset.expected)
        executor.command_mock.assert_called_once_with(
            '/usr/bin/code',
            '--wait',
            '/configs/config.yaml',
        )
