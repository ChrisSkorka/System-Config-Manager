# pyright: strict

import subprocess

from dataclasses import dataclass
from pathlib import PurePath

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
        input_editor: str | None
        fixture_paths_by_name: dict[str, str]
        expected: tuple[str, ...]

    @datasets({
        'configured editor without arguments': ResolveDataset(
            input_platform='linux',
            input_editor='nano',
            fixture_paths_by_name={'nano': '/usr/bin/nano'},
            expected=('/usr/bin/nano',),
        ),
        'configured editor with arguments': ResolveDataset(
            input_platform='linux',
            input_editor='code --wait',
            fixture_paths_by_name={'code': '/usr/bin/code'},
            expected=('/usr/bin/code', '--wait'),
        ),
        'configured editor wins over the fallbacks': ResolveDataset(
            input_platform='linux',
            input_editor='vim',
            fixture_paths_by_name={
                'editor': '/usr/bin/editor',
                'vim': '/usr/bin/vim',
            },
            expected=('/usr/bin/vim',),
        ),
        'quoted windows path with spaces keeps its backslashes': ResolveDataset(
            input_platform='win32',
            input_editor=r'"C:\Program Files\Editor\editor.exe" --wait',
            fixture_paths_by_name={
                r'C:\Program Files\Editor\editor.exe':
                    r'C:\Program Files\Editor\editor.exe',
            },
            expected=(r'C:\Program Files\Editor\editor.exe', '--wait'),
        ),
        'linux prefers the editor alternative': ResolveDataset(
            input_platform='linux',
            input_editor=None,
            fixture_paths_by_name={
                'editor': '/usr/bin/editor',
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/editor',),
        ),
        'linux without the editor alternative uses nano': ResolveDataset(
            input_platform='linux',
            input_editor=None,
            fixture_paths_by_name={
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/nano',),
        ),
        'linux falls back to vi': ResolveDataset(
            input_platform='linux',
            input_editor=None,
            fixture_paths_by_name={'vi': '/bin/vi'},
            expected=('/bin/vi',),
        ),
        'other posix platforms use the linux chain': ResolveDataset(
            input_platform='freebsd14',
            input_editor=None,
            fixture_paths_by_name={'vim': '/usr/local/bin/vim'},
            expected=('/usr/local/bin/vim',),
        ),
        'macos skips the editor alternative': ResolveDataset(
            input_platform='darwin',
            input_editor=None,
            fixture_paths_by_name={
                'editor': '/usr/local/bin/editor',
                'vim': '/usr/bin/vim',
            },
            expected=('/usr/bin/vim',),
        ),
        'macos prefers nano': ResolveDataset(
            input_platform='darwin',
            input_editor=None,
            fixture_paths_by_name={
                'nano': '/usr/bin/nano',
                'vi': '/usr/bin/vi',
            },
            expected=('/usr/bin/nano',),
        ),
        'windows uses notepad': ResolveDataset(
            input_platform='win32',
            input_editor=None,
            fixture_paths_by_name={
                'vim': r'C:\Program Files\Git\usr\bin\vim.exe',
                'notepad': r'C:\Windows\system32\notepad.exe',
            },
            expected=(r'C:\Windows\system32\notepad.exe',),
        ),
    })
    def test_get_editor_command_returns(self, dataset: ResolveDataset) -> None:
        """Test that the configured or fallback editor is resolved."""

        # Arrange
        resolver = EditorResolver(
            platform=dataset.input_platform,
            which=MockWhich(dataset.fixture_paths_by_name),
        )

        # Act
        actual = resolver.get_editor_command(dataset.input_editor)

        # Assert
        self.assertEqual(actual, dataset.expected)

    @dataclass
    class ErrorDataset:
        input_platform: str
        input_editor: str | None
        fixture_paths_by_name: dict[str, str]
        expected_message: str

    @datasets({
        'configured editor is not installed': ErrorDataset(
            input_platform='linux',
            input_editor='code --wait',
            fixture_paths_by_name={'nano': '/usr/bin/nano'},
            expected_message="Editor 'code' from 'system-config-manager.editor' was not found",
        ),
        'unquoted windows path with spaces is split': ErrorDataset(
            input_platform='win32',
            input_editor=r'C:\Program Files\Editor\editor.exe --wait',
            fixture_paths_by_name={'notepad': r'C:\Windows\notepad.exe'},
            expected_message="Editor 'C:Program' from 'system-config-manager.editor' was not found",
        ),
        'configured editor has unbalanced quotes': ErrorDataset(
            input_platform='linux',
            input_editor='"code --wait',
            fixture_paths_by_name={'code': '/usr/bin/code'},
            expected_message="Invalid 'system-config-manager.editor': No closing quotation",
        ),
        'configured editor is only quotes': ErrorDataset(
            input_platform='linux',
            input_editor='""',
            fixture_paths_by_name={},
            expected_message="Editor '' from 'system-config-manager.editor' was not found",
        ),
        'no fallback editor is installed on linux': ErrorDataset(
            input_platform='linux',
            input_editor=None,
            fixture_paths_by_name={'notepad': '/usr/bin/notepad'},
            expected_message="No editor found (tried editor, nano, vim, vi), "
            + "set one with 'system-config-manager.editor' in your config",
        ),
        'no fallback editor is installed on windows': ErrorDataset(
            input_platform='win32',
            input_editor=None,
            fixture_paths_by_name={'vim': r'C:\vim.exe'},
            expected_message="No editor found (tried notepad), "
            + "set one with 'system-config-manager.editor' in your config",
        ),
    })
    def test_get_editor_command_raises(self, dataset: ErrorDataset) -> None:
        """Test that an unusable or missing editor is a validation error."""

        # Arrange
        resolver = EditorResolver(
            platform=dataset.input_platform,
            which=MockWhich(dataset.fixture_paths_by_name),
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            resolver.get_editor_command(dataset.input_editor)

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
            PurePath('/configs/config.yaml'),
        )

        # Assert
        self.assertEqual(actual, dataset.expected)
        executor.command_mock.assert_called_once_with(
            '/usr/bin/code',
            '--wait',
            '/configs/config.yaml',
        )
