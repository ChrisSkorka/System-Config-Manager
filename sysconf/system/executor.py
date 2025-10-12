# pyright: strict

import subprocess
from abc import ABC, abstractmethod


class SystemExecutor(ABC):
    """
    Abstract base class for executing system commands.
    """

    @abstractmethod
    def command(self, *command: str) -> None:
        """
        Run a command/executable with arguments

        Notes:
        - this will encode arguments as needed
        - this will not invoke a shell, it will call the executable directly
        """

        pass  # pragma: no cover

    @abstractmethod
    def shell(self, script: str) -> None:
        """
        Run a shell script/command line

        Notes:
        - this will invoke a shell, so shell features like redirection, pipes, 
          etc will work
        - this will not encode arguments, the script is passed as-is to the shell
        """

        pass  # pragma: no cover


class LiveSystemExecutor(SystemExecutor):
    """
    Executor that actually runs system commands.
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, LiveSystemExecutor)

    def command(self, *command: str) -> None:
        cmd_line = subprocess.list2cmdline(command)
        print('$', cmd_line)
        process: subprocess.CompletedProcess[bytes] = subprocess.run(command)
        print()  # empty line

        if process.returncode != 0:
            raise CommandException(cmd_line, process)

    def shell(self, script: str) -> None:
        print('$', script)
        process: subprocess.CompletedProcess[bytes] = subprocess.run(
            script,
            shell=True,
        )
        print()  # empty line

        if process.returncode != 0:
            raise CommandException(script, process)


class PreviewSystemExecutor(SystemExecutor):
    """
    Executor that only prints the commands instead of executing them.
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, PreviewSystemExecutor)

    def command(self, *command: str) -> None:
        print(subprocess.list2cmdline(command))
        print()  # empty line

    def shell(self, script: str) -> None:
        print(script)
        print()  # empty line


class CommandException(Exception):
    """
    Exception raised when a shell/cmd/cli command fails.
    """

    def __init__(
        self,
        cmdline: str,
        process: subprocess.CompletedProcess[bytes],
    ) -> None:
        super().__init__()

        self.cmdline: str = cmdline
        self.process: subprocess.CompletedProcess[bytes] = process

    def __str__(self) -> str:
        return f"Command '{self.cmdline}' failed with exit code {self.process.returncode}"
