# pyright: strict

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Callable, TypeVar, Generic


class FailureResolution(ABC):

    @abstractmethod
    def get_key(self) -> str:
        """
        Get the keys associated with this failure resolution.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_prompt(self) -> str:
        """
        Get the prompt to display to the user for this resolution.
        """
        pass  # pragma: no cover


T = TypeVar('T', bound=FailureResolution | None)
FR = TypeVar('FR', bound=FailureResolution)


class ErrorHandler(ABC, Generic[T]):
    """
    Abstract base class for error handlers.

    An error handler tries to run a callable and tries to handle, retry, or 
    ignore errors that occur during the execution of the task according to a 
    policy.
    """

    class Status(Enum):
        SUCCESS = auto()
        SKIPPED = auto()
        FAILED = auto()

    @abstractmethod
    def try_run(self, task: Callable[[], None]) -> TryRunResult[T]:
        """
        Try to run the given function and handle any errors that occur.

        When an error occurs, attempt to handle it according to some policy.
        """
        pass  # pragma: no cover


class FailingErrorHandler(ErrorHandler[None]):
    """
    An error handler that always fails when an error occurs.
    """

    def try_run(self, task: Callable[[], None]) -> TryRunResult[None]:
        try:
            task()
            return TryRunResult(ErrorHandler.Status.SUCCESS)
        except Exception:
            return TryRunResult(ErrorHandler.Status.FAILED)


class PromptUserErrorHandler(ErrorHandler[FR]):
    """
    An error handler that prompts the user for input when an error occurs.

    The user can choose to retry, skip, abort, or mark the action as successful.

    Notes:
    - If a task fails but the user chooses to mark it as successful, the caller
      will not know about the failure
    - The user gets up to 5 attempts to make a selection before a failed status
      is returned
    - Does not return or raise the exception in the failure status case
    - Only selected Exception types are caught, all others are propagated
    """

    def __init__(
        self,
        *exceptions: type[Exception],
        failure_resolutions: tuple[FR, ...],
    ) -> None:
        super().__init__()

        self.exceptions = tuple(exceptions)
        self.failure_resolutions = failure_resolutions

    def try_run(self, task: Callable[[], None]) -> TryRunResult[FR]:
        for _ in range(5):  # Limit to 5 attempts
            try:
                task()
                return TryRunResult(ErrorHandler.Status.SUCCESS)
            # todo: should we catch all exceptions?
            except self.exceptions as e:

                # print message & options
                print('An error occurred while executing the action:')
                print(str(e))
                print()  # Empty line
                print('Choose an option:')
                print('[r] Retry')
                print('[s] Skip')
                print('[m] Mark as successful')
                for resolution in self.failure_resolutions:
                    print(f'[{resolution.get_key()}] {resolution.get_prompt()}')
                # todo: help option

                # compute keys
                failed_resolution_map = {
                    res.get_key(): res for res in self.failure_resolutions}
                keys = [
                    'r',
                    's',
                    'm',
                    *failed_resolution_map.keys()
                ]

                # prompt & parse user input
                prompt = f'{'/'.join(keys)}: '
                choice = input(prompt).strip().lower()
                match choice:
                    case 'r':
                        continue
                    case 's':
                        return TryRunResult(ErrorHandler.Status.SKIPPED)
                    case 'm':
                        return TryRunResult(ErrorHandler.Status.SUCCESS)
                    case _ as choice:
                        if choice in failed_resolution_map:
                            return TryRunResult(
                                ErrorHandler.Status.FAILED,
                                failure_resolution=failed_resolution_map[choice],
                            )
                        print('Invalid choice. Please try again.')

        return TryRunResult(ErrorHandler.Status.FAILED)


class TryRunResult(Generic[T]):
    """
    Represents the result of trying to run a task with an error handler.
    """

    def __init__(
        self,
        status: ErrorHandler.Status,
        failure_resolution: T | None = None,
    ) -> None:
        self.status = status
        self.failure_resolution = failure_resolution
