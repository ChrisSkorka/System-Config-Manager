# pyright: strict

import subprocess
from abc import ABC, abstractmethod
from typing import Sequence


class SystemExecutor(ABC):
    """
    Abstract base class for executing system commands.
    """

    @abstractmethod
    def exec(self, *command: str) -> None:
        pass


class LiveSystemExecutor(SystemExecutor):
    """
    Executor that actually runs system commands.

    !Currently only printing to allow safe development & testing!
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, LiveSystemExecutor)

    def exec(self, *command: str) -> None:
        print('>', subprocess.list2cmdline(command))
        completed = subprocess.run(command)

        if completed.returncode != 0:
            raise CommandException(command, completed)


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
    Exception raised when a shell command fails.
    """

    def __init__(
        self,
        command: Sequence[str],
        process: subprocess.CompletedProcess[bytes],
    ) -> None:
        command = subprocess.list2cmdline(command)
        super().__init__(
            f"Command '{command}' failed with exit code {process.returncode}"
        )

        self.command: str = command
        self.process: subprocess.CompletedProcess[bytes] = process
