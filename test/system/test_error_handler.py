# pyright: strict

from dataclasses import dataclass
from unittest.mock import call, patch

from sysconf.system.error_handler import ErrorHandler, PromptUserErrorHandler
from test.datasets import datasets
from test.test_case import TestCase


class SequencedTask:
    """
    A callable task that raises a configured result per call.

    A `None` result means the call succeeds. Once the configured results are
    exhausted the last result repeats, so a single failing result models a task
    that always fails.
    """

    def __init__(self, results: tuple[BaseException | None, ...]) -> None:
        self.results = results
        self.calls = 0

    def __call__(self) -> None:
        index = min(self.calls, len(self.results) - 1)
        result = self.results[index]
        self.calls += 1

        if result is not None:
            raise result


class TestPromptUserErrorHandler(TestCase):
    """Test the interactive retry/skip/abort/mark prompt loop."""

    @dataclass
    class TryRunDataset:
        fixture_task_results: tuple[BaseException | None, ...]
        fixture_user_inputs: tuple[str, ...]
        input_handled_exceptions: tuple[type[Exception], ...] = (Exception,)
        expected_status: ErrorHandler.Status = ErrorHandler.Status.SUCCESS
        expected_task_calls: int = 1
        expected_prompt_calls: int = 0

    @datasets({
        'task succeeds immediately': TryRunDataset(
            fixture_task_results=(None,),
            fixture_user_inputs=(),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=1,
            expected_prompt_calls=0,
        ),
        'user skips the failing action': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('s',),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'user aborts the failing action': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('a',),
            expected_status=ErrorHandler.Status.FAILED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'user marks the failing action as successful': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('m',),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'user retries and the task then succeeds': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'), None),
            fixture_user_inputs=('r',),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=2,
            expected_prompt_calls=1,
        ),
        'user retries twice before success': TryRunDataset(
            fixture_task_results=(
                RuntimeError('boom'),
                RuntimeError('boom again'),
                None,
            ),
            fixture_user_inputs=('r', 'r'),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=3,
            expected_prompt_calls=2,
        ),
        'retries are exhausted after five attempts': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('r', 'r', 'r', 'r', 'r'),
            expected_status=ErrorHandler.Status.FAILED,
            expected_task_calls=5,
            expected_prompt_calls=5,
        ),
        'invalid choice consumes an attempt then user skips': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('x', 's'),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=2,
            expected_prompt_calls=2,
        ),
        'choice is trimmed and lowercased': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('  S  ',),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'only the configured exception type is caught': TryRunDataset(
            fixture_task_results=(ValueError('bad value'),),
            fixture_user_inputs=('a',),
            input_handled_exceptions=(ValueError,),
            expected_status=ErrorHandler.Status.FAILED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
    })
    def test_try_run(self, dataset: TryRunDataset) -> None:
        """Test the status, task attempts and prompts for each user choice."""

        # Arrange
        handler = PromptUserErrorHandler(*dataset.input_handled_exceptions)
        task = SequencedTask(dataset.fixture_task_results)

        # Act
        with patch('builtins.input', side_effect=dataset.fixture_user_inputs) as mock_input, \
                patch('builtins.print'):
            actual = handler.try_run(task)

        # Assert
        self.assertEqual(actual, dataset.expected_status)
        self.assertEqual(task.calls, dataset.expected_task_calls)
        self.assertEqual(mock_input.call_count, dataset.expected_prompt_calls)

    @dataclass
    class UnhandledDataset:
        fixture_task_results: tuple[BaseException | None, ...]
        input_handled_exceptions: tuple[type[Exception], ...]
        expected_exception: type[BaseException]

    @datasets({
        'different exception type': UnhandledDataset(
            fixture_task_results=(RuntimeError('boom'),),
            input_handled_exceptions=(ValueError,),
            expected_exception=RuntimeError,
        ),
        'no exception types configured': UnhandledDataset(
            fixture_task_results=(RuntimeError('boom'),),
            input_handled_exceptions=(),
            expected_exception=RuntimeError,
        ),
        'keyboard interrupt is not caught': UnhandledDataset(
            fixture_task_results=(KeyboardInterrupt(),),
            input_handled_exceptions=(Exception,),
            expected_exception=KeyboardInterrupt,
        ),
    })
    def test_try_run_propagates_unhandled_exceptions(
        self,
        dataset: UnhandledDataset,
    ) -> None:
        """Test that exceptions outside the configured types are not caught."""

        # Arrange
        handler = PromptUserErrorHandler(*dataset.input_handled_exceptions)
        task = SequencedTask(dataset.fixture_task_results)

        # Act & Assert
        with patch('builtins.input') as mock_input, patch('builtins.print'):
            with self.assertRaises(dataset.expected_exception):
                handler.try_run(task)

        mock_input.assert_not_called()

    def test_try_run_prints_the_available_options(self) -> None:
        """Test that the failure message and all options are shown to the user."""

        # Arrange
        handler = PromptUserErrorHandler(Exception)
        task = SequencedTask((RuntimeError('boom'),))

        # Act
        with patch('builtins.input', side_effect=('a',)), \
                patch('builtins.print') as mock_print:
            handler.try_run(task)

        # Assert
        mock_print.assert_has_calls(
            [
                call('An error occurred while executing the action:'),
                call('boom'),
                call(),
                call('Choose an option:'),
                call('[r] Retry'),
                call('[s] Skip'),
                call('[a] Abort'),
                call('[m] Mark as successful'),
            ],
            any_order=False,
        )
