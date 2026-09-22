# pyright: strict

from dataclasses import dataclass
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import call, patch

from sysconf.system.executor import (
    CommandException,
    LiveSystemExecutor,
    PreviewSystemExecutor,
)
from test.datasets import datasets
from test.system.mock_subprocess import create_mock_run
from test.test_case import TestCase


class TestLiveSystemExecutor(TestCase):
    """Test that LiveSystemExecutor really runs commands and scripts."""

    @dataclass
    class CommandDataset:
        input_command: tuple[str, ...]
        expected_cmdline: str

    @datasets({
        'simple command': CommandDataset(
            input_command=('gsettings', 'reset', 'org.schema', 'key'),
            expected_cmdline='gsettings reset org.schema key',
        ),
        'argument with spaces is quoted': CommandDataset(
            input_command=('gsettings', 'set', 'org.schema', 'key', 'two words'),
            expected_cmdline='gsettings set org.schema key "two words"',
        ),
        'single argument': CommandDataset(
            input_command=('true',),
            expected_cmdline='true',
        ),
    })
    def test_command_success(self, dataset: CommandDataset) -> None:
        """Test that the command is run directly and echoed to stdout."""

        # Arrange
        executor = LiveSystemExecutor()
        mock_run = create_mock_run(CompletedProcess(args=(), returncode=0))

        # Act
        with patch('subprocess.run', mock_run), patch('builtins.print') as mock_print:
            executor.command(*dataset.input_command)

        # Assert
        mock_run.assert_called_once_with(dataset.input_command)
        mock_print.assert_has_calls(
            [call('$', dataset.expected_cmdline), call()],
            any_order=False,
        )

    def test_command_raises_on_non_zero_exit(self) -> None:
        """Test that a failing command raises a CommandException."""

        # Arrange
        executor = LiveSystemExecutor()
        process = CompletedProcess[bytes](args=(), returncode=3)
        mock_run = create_mock_run(process)

        # Act & Assert
        with patch('subprocess.run', mock_run), patch('builtins.print'):
            with self.assertRaises(CommandException) as context:
                executor.command('false', 'arg')

        self.assertEqual(context.exception.cmdline, 'false arg')
        self.assertIs(context.exception.process, process)

    @dataclass
    class ShellDataset:
        input_script: str

    @datasets({
        'simple script': ShellDataset(
            input_script='sudo apt install -y git',
        ),
        'script with a pipe': ShellDataset(
            input_script='cat /etc/hosts | grep localhost',
        ),
        'multiline script': ShellDataset(
            input_script='rm -f /tmp/a;\nln -sf /tmp/b /tmp/a;',
        ),
    })
    def test_shell_success(self, dataset: ShellDataset) -> None:
        """Test that the script is passed to the shell verbatim."""

        # Arrange
        executor = LiveSystemExecutor()
        mock_run = create_mock_run(CompletedProcess(args=(), returncode=0))

        # Act
        with patch('subprocess.run', mock_run), patch('builtins.print') as mock_print:
            executor.shell(dataset.input_script)

        # Assert
        mock_run.assert_called_once_with(dataset.input_script, shell=True)
        mock_print.assert_has_calls(
            [call('$', dataset.input_script), call()],
            any_order=False,
        )

    def test_shell_raises_on_non_zero_exit(self) -> None:
        """Test that a failing script raises a CommandException."""

        # Arrange
        executor = LiveSystemExecutor()
        process = CompletedProcess[bytes](args=(), returncode=1)
        mock_run = create_mock_run(process)

        # Act & Assert
        with patch('subprocess.run', mock_run), patch('builtins.print'):
            with self.assertRaises(CommandException) as context:
                executor.shell('exit 1')

        self.assertEqual(context.exception.cmdline, 'exit 1')
        self.assertIs(context.exception.process, process)

    @dataclass
    class EqualityDataset:
        input_other: Any
        expected_equal: bool

    @datasets({
        'another live executor': EqualityDataset(
            input_other=LiveSystemExecutor(),
            expected_equal=True,
        ),
        'a preview executor': EqualityDataset(
            input_other=PreviewSystemExecutor(),
            expected_equal=False,
        ),
        'a string': EqualityDataset(
            input_other='live',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that live executors compare by type."""

        # Arrange
        executor = LiveSystemExecutor()

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(executor, dataset.input_other)
        else:
            self.assertNotEqual(executor, dataset.input_other)


class TestPreviewSystemExecutor(TestCase):
    """Test that PreviewSystemExecutor only prints and never executes."""

    @dataclass
    class PreviewDataset:
        input_command: tuple[str, ...] | None
        input_script: str | None
        expected_output: str

    @datasets({
        'command is printed as a command line': PreviewDataset(
            input_command=('gsettings', 'set', 'org.schema', 'key', 'two words'),
            input_script=None,
            expected_output='gsettings set org.schema key "two words"',
        ),
        'command without arguments': PreviewDataset(
            input_command=('true',),
            input_script=None,
            expected_output='true',
        ),
        'script is printed verbatim': PreviewDataset(
            input_command=None,
            input_script='sudo apt install -y git',
            expected_output='sudo apt install -y git',
        ),
        'multiline script is printed verbatim': PreviewDataset(
            input_command=None,
            input_script='rm -f /tmp/a;\nln -sf /tmp/b /tmp/a;',
            expected_output='rm -f /tmp/a;\nln -sf /tmp/b /tmp/a;',
        ),
    })
    def test_preview_does_not_execute(self, dataset: PreviewDataset) -> None:
        """Test that the command/script is printed and subprocess is never called."""

        # Arrange
        executor = PreviewSystemExecutor()
        mock_run = create_mock_run()

        # Act
        with patch('subprocess.run', mock_run), patch('builtins.print') as mock_print:
            if dataset.input_command is not None:
                executor.command(*dataset.input_command)
            else:
                assert dataset.input_script is not None
                executor.shell(dataset.input_script)

        # Assert
        mock_run.assert_not_called()
        mock_print.assert_has_calls(
            [call(dataset.expected_output), call()],
            any_order=False,
        )

    @dataclass
    class EqualityDataset:
        input_other: Any
        expected_equal: bool

    @datasets({
        'another preview executor': EqualityDataset(
            input_other=PreviewSystemExecutor(),
            expected_equal=True,
        ),
        'a live executor': EqualityDataset(
            input_other=LiveSystemExecutor(),
            expected_equal=False,
        ),
        'a string': EqualityDataset(
            input_other='preview',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that preview executors compare by type."""

        # Arrange
        executor = PreviewSystemExecutor()

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(executor, dataset.input_other)
        else:
            self.assertNotEqual(executor, dataset.input_other)


class TestCommandException(TestCase):
    """Test the failed command exception message."""

    @dataclass
    class ExceptionDataset:
        input_cmdline: str
        input_returncode: int
        expected_message: str

    @datasets({
        'simple command': ExceptionDataset(
            input_cmdline='false',
            input_returncode=1,
            expected_message="Command 'false' failed with exit code 1",
        ),
        'command with arguments': ExceptionDataset(
            input_cmdline='sudo apt install -y git',
            input_returncode=100,
            expected_message="Command 'sudo apt install -y git' failed with exit code 100",
        ),
        'signal exit code': ExceptionDataset(
            input_cmdline='sleep 10',
            input_returncode=-9,
            expected_message="Command 'sleep 10' failed with exit code -9",
        ),
    })
    def test_str(self, dataset: ExceptionDataset) -> None:
        """Test that the exception renders the command line and exit code."""

        # Arrange
        process = CompletedProcess[bytes](
            args=(),
            returncode=dataset.input_returncode,
        )

        # Act
        exception = CommandException(dataset.input_cmdline, process)

        # Assert
        self.assertEqual(str(exception), dataset.expected_message)
