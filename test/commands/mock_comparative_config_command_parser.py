# pyright: strict

from typing import TypeVar

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.error_handler import ErrorHandler, FailureResolution
from sysconf.system.executor import SystemExecutor
from test.system.mock_system_manager import MockSystemManager


FR = TypeVar('FR', bound=FailureResolution | None)


class MockComparativeConfigCommandParser(ComparativeConfigCommandParser):
    """
    Mock parser that returns a mock system manager for the configured configs.
    """

    def __init__(self, old_config: SystemConfig, new_config: SystemConfig) -> None:
        # Don't call super().__init__() — we don't need real paths/file_reader
        self.old_config = old_config
        self.new_config = new_config

    @classmethod
    def default(cls) -> 'MockComparativeConfigCommandParser':
        empty_config = SystemConfig.create_from_entries((), (), (), ())
        return cls(old_config=empty_config, new_config=empty_config)

    def get_system_manager(
        self,
        executor: SystemExecutor,
        error_handler: ErrorHandler[FR],
    ) -> SystemManager[FR]:
        return MockSystemManager[FR](
            old_config=self.old_config,
            new_config=self.new_config,
        )
