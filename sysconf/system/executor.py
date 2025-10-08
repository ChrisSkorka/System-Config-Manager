# pyright: strict

import subprocess
from abc import ABC, abstractmethod


class SystemExecutor(ABC):
    """
    Abstract base class for executing system commands.
    """

    @abstractmethod
    def exec(self, *command: str) -> None:
        pass  # pragma: no cover


class LiveSystemExecutor(SystemExecutor):
    """
    Executor that actually runs system commands.

    !Currently only printing to allow safe development & testing!
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, LiveSystemExecutor)

    def exec(self, *command: str) -> None:
        print(subprocess.list2cmdline(command))
        process: subprocess.CompletedProcess[bytes] = subprocess.run(command)

        if process.returncode != 0:
            raise CommandException(process)


class PreviewSystemExecutor(SystemExecutor):
    """
    Executor that only prints the commands instead of executing them.
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, PreviewSystemExecutor)

    def exec(self, *command: str) -> None:
        print(subprocess.list2cmdline(command))


class CommandException(Exception):
    """
    Exception raised when a shell/cmd/cli command fails.
    """

    def __init__(
        self,
        process: subprocess.CompletedProcess[bytes],
    ) -> None:
        super().__init__()

        self.process: subprocess.CompletedProcess[bytes] = process

    def __str__(self) -> str:
        cmdline = subprocess.list2cmdline(self.process.args)
        return f"Command '{cmdline}' failed with exit code {self.process.returncode}"
