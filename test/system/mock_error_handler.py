# pyright: strict

from typing import Callable

from sysconf.system.error_handler import ErrorHandler


class MockSuccessErrorHandler(ErrorHandler):

    def try_run(self, task: Callable[[], None]) -> ErrorHandler.Status:
        task()
        return ErrorHandler.Status.SUCCESS


class MockFailErrorHandler(ErrorHandler):

    def try_run(self, task: Callable[[], None]) -> ErrorHandler.Status:
        task()
        return ErrorHandler.Status.FAILED


class MockSkipErrorHandler(ErrorHandler):

    def try_run(self, task: Callable[[], None]) -> ErrorHandler.Status:
        task()
        return ErrorHandler.Status.SKIPPED


class MockSequencedErrorHandler(ErrorHandler):
    """
    Returns a configured status for each successive call.

    Once the configured statuses are exhausted the last one repeats, so a single
    status models a handler that always returns it.
    """

    def __init__(self, *statuses: ErrorHandler.Status) -> None:
        super().__init__()

        assert len(statuses) > 0, 'At least one status is required'

        self.statuses = statuses
        self.calls = 0

    def try_run(self, task: Callable[[], None]) -> ErrorHandler.Status:
        task()

        index = min(self.calls, len(self.statuses) - 1)
        self.calls += 1

        return self.statuses[index]
