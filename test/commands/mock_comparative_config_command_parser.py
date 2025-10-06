# pyright: strict

from sysconf.commands.apply_command import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemManager
from test.system.mock_system_manager import MockSystemManager


class MockComparativeConfigCommandParser(ComparativeConfigCommandParser):
    """
    Mock parser that allows setting a mock system manager for testing.
    """

    # def __init__(self, system_manager: SystemManager) -> None:
    #     super().__init__(system_manager)

    #     self.system_manager = system_manager

    @classmethod
    def default(
        cls, 
        system_manager: SystemManager | None = None,
    ) -> 'MockComparativeConfigCommandParser':
        
        system_manager = system_manager or MockSystemManager.default()
        return cls(system_manager=system_manager)