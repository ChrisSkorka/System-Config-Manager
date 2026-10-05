# pyright: strict

from dataclasses import dataclass
from unittest.mock import call, patch

from sysconf.system.error_handler import ErrorHandler, FailingErrorHandler, PromptUserErrorHandler
from test.datasets import datasets
from test.system.mock_error_handler import MockFailureResolution
from test.test_case import TestCase


ALL_RESOLUTIONS = (MockFailureResolution.ABORT, MockFailureResolution.EDIT)


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
    """Test the interactive retry/skip/mark/resolution prompt loop."""

    @dataclass
    class TryRunDataset:
        fixture_task_results: tuple[BaseException | None, ...]
        fixture_user_inputs: tuple[str, ...]
        input_handled_exceptions: tuple[type[Exception], ...] = (Exception,)
        input_failure_resolutions: tuple[MockFailureResolution, ...] = ALL_RESOLUTIONS
        expected_status: ErrorHandler.Status = ErrorHandler.Status.SUCCESS
        expected_failure_resolution: MockFailureResolution | None = None
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
        'skip': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('s',),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'mark as successful': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('m',),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'first failure resolution': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('a',),
            expected_status=ErrorHandler.Status.FAILED,
            expected_failure_resolution=MockFailureResolution.ABORT,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'second failure resolution': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('e',),
            expected_status=ErrorHandler.Status.FAILED,
            expected_failure_resolution=MockFailureResolution.EDIT,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'retry once': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'), None),
            fixture_user_inputs=('r',),
            expected_status=ErrorHandler.Status.SUCCESS,
            expected_task_calls=2,
            expected_prompt_calls=1,
        ),
        'retry twice': TryRunDataset(
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
        'retry five times': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('r', 'r', 'r', 'r', 'r'),
            expected_status=ErrorHandler.Status.FAILED,
            expected_task_calls=5,
            expected_prompt_calls=5,
        ),
        'invalid choice then skip': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('x', 's'),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=2,
            expected_prompt_calls=2,
        ),
        'unconfigured failure resolution key then skip': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('e', 's'),
            input_failure_resolutions=(MockFailureResolution.ABORT,),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=2,
            expected_prompt_calls=2,
        ),
        'no failure resolutions configured': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('a', 's'),
            input_failure_resolutions=(),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=2,
            expected_prompt_calls=2,
        ),
        'padded uppercase choice': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            fixture_user_inputs=('  S  ',),
            expected_status=ErrorHandler.Status.SKIPPED,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
        'configured exception type': TryRunDataset(
            fixture_task_results=(ValueError('bad value'),),
            fixture_user_inputs=('a',),
            input_handled_exceptions=(ValueError,),
            expected_status=ErrorHandler.Status.FAILED,
            expected_failure_resolution=MockFailureResolution.ABORT,
            expected_task_calls=1,
            expected_prompt_calls=1,
        ),
    })
    def test_try_run(self, dataset: TryRunDataset) -> None:
        """Test the status, task attempts and prompts for each user choice."""

        # Arrange
        handler = PromptUserErrorHandler(
            *dataset.input_handled_exceptions,
            failure_resolutions=dataset.input_failure_resolutions,
        )
        task = SequencedTask(dataset.fixture_task_results)

        # Act
        with patch('builtins.input', side_effect=dataset.fixture_user_inputs) as mock_input, \
                patch('builtins.print'):
            actual = handler.try_run(task)

        # Assert
        self.assertEqual(actual.status, dataset.expected_status)
        self.assertEqual(
            actual.failure_resolution,
            dataset.expected_failure_resolution,
        )
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
        'keyboard interrupt': UnhandledDataset(
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
        handler = PromptUserErrorHandler(
            *dataset.input_handled_exceptions,
            failure_resolutions=ALL_RESOLUTIONS,
        )
        task = SequencedTask(dataset.fixture_task_results)

        # Act & Assert
        with patch('builtins.input') as mock_input, patch('builtins.print'):
            with self.assertRaises(dataset.expected_exception):
                handler.try_run(task)

        mock_input.assert_not_called()

    @dataclass
    class PrintDataset:
        input_failure_resolutions: tuple[MockFailureResolution, ...]
        expected_options: list[str]
        expected_prompt: str

    @datasets({
        'no failure resolutions': PrintDataset(
            input_failure_resolutions=(),
            expected_options=[
                '[r] Retry',
                '[s] Skip',
                '[m] Mark as successful',
            ],
            expected_prompt='r/s/m: ',
        ),
        'all failure resolutions': PrintDataset(
            input_failure_resolutions=ALL_RESOLUTIONS,
            expected_options=[
                '[r] Retry',
                '[s] Skip',
                '[m] Mark as successful',
                '[a] Abort',
                '[e] Edit config',
            ],
            expected_prompt='r/s/m/a/e: ',
        ),
    })
    def test_try_run_prints_the_available_options(
        self,
        dataset: PrintDataset,
    ) -> None:
        """Test that the failure message and all options are shown to the user."""

        # Arrange
        handler = PromptUserErrorHandler(
            Exception,
            failure_resolutions=dataset.input_failure_resolutions,
        )
        task = SequencedTask((RuntimeError('boom'),))

        # Act
        with patch('builtins.input', side_effect=('s',)) as mock_input, \
                patch('builtins.print') as mock_print:
            handler.try_run(task)

        # Assert
        self.assertEqual(
            mock_print.call_args_list,
            [
                call('An error occurred while executing the action:'),
                call('boom'),
                call(),
                call('Choose an option:'),
                *(call(option) for option in dataset.expected_options),
            ],
        )
        mock_input.assert_called_once_with(dataset.expected_prompt)


class TestFailingErrorHandler(TestCase):
    """Test the non-interactive handler that fails on any error."""

    @dataclass
    class TryRunDataset:
        fixture_task_results: tuple[BaseException | None, ...]
        expected_status: ErrorHandler.Status

    @datasets({
        'task succeeds': TryRunDataset(
            fixture_task_results=(None,),
            expected_status=ErrorHandler.Status.SUCCESS,
        ),
        'task raises': TryRunDataset(
            fixture_task_results=(RuntimeError('boom'),),
            expected_status=ErrorHandler.Status.FAILED,
        ),
    })
    def test_try_run_returns(self, dataset: TryRunDataset) -> None:
        """Test the status for a task that succeeds or raises."""

        # Arrange
        handler = FailingErrorHandler()
        task = SequencedTask(dataset.fixture_task_results)

        # Act
        with patch('builtins.input') as mock_input:
            actual = handler.try_run(task)

        # Assert
        self.assertEqual(actual.status, dataset.expected_status)
        self.assertIsNone(actual.failure_resolution)
        self.assertEqual(task.calls, 1)
        mock_input.assert_not_called()

    @dataclass
    class RaiseDataset:
        fixture_task_results: tuple[BaseException | None, ...]
        expected_exception: type[BaseException]

    @datasets({
        'keyboard interrupt': RaiseDataset(
            fixture_task_results=(KeyboardInterrupt(),),
            expected_exception=KeyboardInterrupt,
        ),
    })
    def test_try_run_raises(self, dataset: RaiseDataset) -> None:
        """Test that exceptions other than Exception subclasses propagate."""

        # Arrange
        handler = FailingErrorHandler()
        task = SequencedTask(dataset.fixture_task_results)

        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            handler.try_run(task)
