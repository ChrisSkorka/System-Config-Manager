# pyright: strict

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

from sysconf.config.actions import ShellAction
from sysconf.config.serialization import YamlSerializable
from test.datasets import datasets
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


class TestShellAction(TestCase):
    """Test shell action equality, rendering, execution and deserialization."""

    @dataclass
    class EqualityDataset:
        input_shell_action_1: ShellAction
        input_shell_action_2: Any
        expected_equal: bool

    @datasets({
        'identical scripts': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2=ShellAction('echo "hello"'),
            expected_equal=True,
        ),
        'different scripts': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2=ShellAction('echo "world"'),
            expected_equal=False,
        ),
        'empty scripts': EqualityDataset(
            input_shell_action_1=ShellAction(''),
            input_shell_action_2=ShellAction(''),
            expected_equal=True,
        ),
        'multiline scripts': EqualityDataset(
            input_shell_action_1=ShellAction('line1\nline2\nline3'),
            input_shell_action_2=ShellAction('line1\nline2\nline3'),
            expected_equal=True,
        ),
        'case sensitive comparison': EqualityDataset(
            input_shell_action_1=ShellAction('ECHO "Hello"'),
            input_shell_action_2=ShellAction('echo "Hello"'),
            expected_equal=False,
        ),
        'not equal to string': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2='echo "hello"',
            expected_equal=False,
        ),
        'not equal to int': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2=42,
            expected_equal=False,
        ),
        'not equal to None': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2=None,
            expected_equal=False,
        ),
        'not equal to dict': EqualityDataset(
            input_shell_action_1=ShellAction('echo "hello"'),
            input_shell_action_2={'script': 'echo "hello"'},
            expected_equal=False,
        ),
    })
    def test_equality_with_shell_actions(self, dataset: EqualityDataset) -> None:
        """Test that equality works correctly between ShellAction instances and other types."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_shell_action_1,
                             dataset.input_shell_action_2)
        else:
            self.assertNotEqual(dataset.input_shell_action_1,
                                dataset.input_shell_action_2)

    @dataclass
    class RenderDataset:
        input_script: str
        expected_script: str

    @datasets({
        'simple script': RenderDataset(
            input_script='echo "hello"',
            expected_script='echo "hello"',
        ),
        'multiline script': RenderDataset(
            input_script='#!/bin/bash\necho "line 1"\necho "line 2"',
            expected_script='#!/bin/bash\necho "line 1"\necho "line 2"',
        ),
        'empty script': RenderDataset(
            input_script='',
            expected_script='',
        ),
        'script with special characters': RenderDataset(
            input_script='echo "test" && ls -la | grep "file"',
            expected_script='echo "test" && ls -la | grep "file"',
        ),
    })
    def test_render(self, dataset: RenderDataset) -> None:
        """Test that render returns the script as a string."""

        # Arrange
        action = ShellAction(dataset.input_script)

        # Act
        rendered = action.render()

        # Assert
        self.assertEqual(rendered, dataset.expected_script)
        self.assertIsInstance(rendered, str)

    @dataclass
    class ExecutionDataset:
        input_script: str
        expected_shell: str

    @datasets({
        'simple command': ExecutionDataset(
            input_script='echo "hello"',
            expected_shell='echo "hello"',
        ),
        'multiline script': ExecutionDataset(
            input_script='#!/bin/bash\necho "line 1"\necho "line 2"',
            expected_shell='#!/bin/bash\necho "line 1"\necho "line 2"',
        ),
        'empty script': ExecutionDataset(
            input_script='',
            expected_shell='',
        ),
        'complex pipeline': ExecutionDataset(
            input_script='cat /etc/hosts | grep localhost | wc -l',
            expected_shell='cat /etc/hosts | grep localhost | wc -l',
        ),
    })
    def test_run_executes_with_various_scripts(self, dataset: ExecutionDataset) -> None:
        """Test that run calls executor.shell with the script."""

        # Arrange
        action = ShellAction(dataset.input_script)
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_shell)

    @dataclass
    class DeserializationDataset:
        input_data: str
        expected: ShellAction

    @datasets({
        'simple script': DeserializationDataset(
            input_data='echo "hello"',
            expected=ShellAction('echo "hello"'),
        ),
        'multiline script': DeserializationDataset(
            input_data='#!/bin/bash\necho "line 1"\necho "line 2"',
            expected=ShellAction('#!/bin/bash\necho "line 1"\necho "line 2"'),
        ),
        'empty script': DeserializationDataset(
            input_data='',
            expected=ShellAction(''),
        ),
        'script with special characters': DeserializationDataset(
            input_data='export VAR="value with spaces"\necho $VAR',
            expected=ShellAction('export VAR="value with spaces"\necho $VAR'),
        ),
    })
    def test_create_from_serialized_with_valid_string(self, dataset: DeserializationDataset) -> None:
        """Test that create_from_serialized correctly creates a ShellAction from a string."""

        # Act
        action = ShellAction.create_from_serialized(dataset.input_data)

        # Assert
        self.assertEqual(action, dataset.expected)

    @dataclass
    class InvalidDataDataset:
        input_data: YamlSerializable
        expected_error_message_contains: str

    @datasets({
        'list data': InvalidDataDataset(
            input_data=['echo "hello"'],
            expected_error_message_contains='ShellAction data must be a string/text script',
        ),
        'dict data': InvalidDataDataset(
            input_data={'script': 'echo "hello"'},
            expected_error_message_contains='ShellAction data must be a string/text script',
        ),
        'int data': InvalidDataDataset(
            input_data=42,
            expected_error_message_contains='ShellAction data must be a string/text script',
        ),
    })
    def test_create_from_serialized_with_invalid_data(self, dataset: InvalidDataDataset) -> None:
        """Test that create_from_serialized raises AssertionError for non-string data."""

        # Act & Assert
        with self.assertRaises(AssertionError) as context:
            ShellAction.create_from_serialized(dataset.input_data)

        self.assertIn(dataset.expected_error_message_contains,
                      str(context.exception))
