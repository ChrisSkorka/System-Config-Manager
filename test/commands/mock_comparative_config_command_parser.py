# pyright: strict

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemManager
from sysconf.system.error_handler import ErrorHandler
from sysconf.system.executor import SystemExecutor
from test.system.mock_system_manager import MockSystemManager


class MockComparativeConfigCommandParser(ComparativeConfigCommandParser):
    """
    Mock parser that allows setting a mock system manager for testing.
    """

    def __init__(self, system_manager: SystemManager) -> None:
        # Don't call super().__init__() — we don't need real paths/file_reader
        self._system_manager = system_manager

    @classmethod
    def default(
        cls,
        system_manager: SystemManager | None = None,
    ) -> 'MockComparativeConfigCommandParser':

        system_manager = system_manager or MockSystemManager.default()
        return cls(system_manager=system_manager)

    def get_system_manager(
        self,
        executor: SystemExecutor,
        error_handler: ErrorHandler,
    ) -> SystemManager:
        return self._system_manager
