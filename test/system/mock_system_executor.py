# pyright: strict

from unittest.mock import MagicMock

from sysconf.system.executor import SystemExecutor


class MockSystemExecutor (SystemExecutor):
    """Mock executor that tracks method calls for testing."""

    def __init__(self) -> None:
        self.shell_mock = MagicMock()
        self.command_mock = MagicMock()

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MockSystemExecutor)

    def command(self, *command: str) -> None:
        self.command_mock(*command)

    def shell(self, script: str) -> None:
        self.shell_mock(script)


class MockRaisingSystemExecutor (SystemExecutor):
    """Executor that raises the configured exception for every invocation."""

    def __init__(self, exception: BaseException) -> None:
        self.exception = exception

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MockRaisingSystemExecutor)

    def command(self, *command: str) -> None:
        raise self.exception

    def shell(self, script: str) -> None:
        raise self.exception
