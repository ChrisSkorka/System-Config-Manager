# pyright: strict

# import subprocess
from abc import ABC, abstractmethod


class SystemExecutor(ABC):
    """
    Abstract base class for executing system commands.
    """

    @abstractmethod
    def exec(self, *command: str) -> int:
        pass


class PreviewSystemExecutor(SystemExecutor):
    """
    Executor that only prints the commands instead of executing them.
    """

    def exec(self, *command: str) -> int:
        print(' '.join(command))
        return 0
