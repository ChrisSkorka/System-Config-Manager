# pyright: strict

from typing import Callable

from sysconf.system.error_handler import ErrorHandler, TryRunResult
from sysconf.utils.choice_prompt import ChoicePromptOptionEnum


class MockFailureResolution (ChoicePromptOptionEnum):
    """Resolutions a user can choose for a failed task."""

    ABORT = ('a', 'Abort')
    EDIT = ('e', 'Edit config')


class MockSuccessErrorHandler(ErrorHandler[MockFailureResolution]):

    def try_run(self, task: Callable[[], None]) -> TryRunResult[MockFailureResolution]:
        task()
        return TryRunResult(ErrorHandler.Status.SUCCESS)


class MockFailErrorHandler(ErrorHandler[MockFailureResolution]):
    """Fails every task with the configured failure resolution."""

    def __init__(
        self,
        failure_resolution: MockFailureResolution | None = None,
    ) -> None:
        super().__init__()

        self.failure_resolution = failure_resolution

    def try_run(self, task: Callable[[], None]) -> TryRunResult[MockFailureResolution]:
        task()
        return TryRunResult(
            ErrorHandler.Status.FAILED,
            failure_resolution=self.failure_resolution,
        )


class MockSkipErrorHandler(ErrorHandler[MockFailureResolution]):

    def try_run(self, task: Callable[[], None]) -> TryRunResult[MockFailureResolution]:
        task()
        return TryRunResult(ErrorHandler.Status.SKIPPED)


class MockSequencedErrorHandler(ErrorHandler[MockFailureResolution]):
    """
    Returns a configured status for each successive call.

    - Once the configured statuses are exhausted the last one repeats, so a
      single status models a handler that always returns it
    - The failure resolution is only returned with a failed status
    """

    def __init__(
        self,
        *statuses: ErrorHandler.Status,
        failure_resolution: MockFailureResolution | None = None,
    ) -> None:
        super().__init__()

        assert len(statuses) > 0, 'At least one status is required'

        self.statuses = statuses
        self.failure_resolution = failure_resolution
        self.calls = 0

    def try_run(self, task: Callable[[], None]) -> TryRunResult[MockFailureResolution]:
        task()

        index = min(self.calls, len(self.statuses) - 1)
        self.calls += 1

        status = self.statuses[index]
        failure_resolution = self.failure_resolution \
            if status == ErrorHandler.Status.FAILED \
            else None

        return TryRunResult(status, failure_resolution=failure_resolution)
