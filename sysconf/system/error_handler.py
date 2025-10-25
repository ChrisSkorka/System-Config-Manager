# pyright: strict

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Callable


class ErrorHandler(ABC):
    """
    Abstract base class for error handlers.

    An error handler trys to run a callable and tries to handle, retry, or 
    irgnore errors that occur during the execution of the task according to a 
    policy.
    """

    class Status(Enum):
        SUCCESS = auto()
        SKIPPED = auto()
        FAILED = auto()

    @abstractmethod
    def try_run(self, task: Callable[[], None]) -> Status:
        """
        Try to run the given function and handle any errors that occur.

        When an error occurs, attempt to handle it according to some policy.
        """
        pass  # pragma: no cover


class PromptUserErrorHandler(ErrorHandler):
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

    def __init__(self, *exceptions: type[Exception]) -> None:
        super().__init__()

        self.exceptions = tuple(exceptions)

    def try_run(self, task: Callable[[], None]) -> ErrorHandler.Status:
        for _ in range(5):  # Limit to 5 attempts
            try:
                task()
                return ErrorHandler.Status.SUCCESS
            except self.exceptions as e:
                print('An error occurred while executing the action:')
                print(str(e))
                print()  # Empty line
                print('Choose an option:')
                print('[r] Retry')
                print('[s] Skip')
                print('[a] Abort')
                print('[m] Mark as successful')

                choice = input('r/s/a/m: ').strip().lower()
                match choice:
                    case 'r':
                        continue
                    case 's':
                        return ErrorHandler.Status.SKIPPED
                    case 'a':
                        return ErrorHandler.Status.FAILED
                    case 'm':
                        return ErrorHandler.Status.SUCCESS
                    case _:
                        print('Invalid choice. Please try again.')

        return ErrorHandler.Status.FAILED
