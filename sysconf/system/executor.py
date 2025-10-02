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


class LiveSystemExecutor(SystemExecutor):
    """
    Executor that actually runs system commands.

    !Currently only printing to allow safe development & testing!
    """

    def exec(self, *command: str) -> int:
        print('>', ' '.join(command))
        try:
            # completed = subprocess.run(command)
            # return completed.returncode
            return 0
        except Exception:
            return 1


class PreviewSystemExecutor(SystemExecutor):
    """
    Executor that only prints the commands instead of executing them.
    """

    def exec(self, *command: str) -> int:
        print(' '.join(command))
        return 0
