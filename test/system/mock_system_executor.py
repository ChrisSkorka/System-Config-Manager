# pyright: strict

from unittest.mock import MagicMock
from sysconf.system.executor import SystemExecutor


class MockSystemExecutor (SystemExecutor):

    def __init__(self) -> None:
        self.exec = MagicMock(return_value=None)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MockSystemExecutor)

    def exec(self, *command: str) -> None:
        pass