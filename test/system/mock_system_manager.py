# pyright: strict

from typing import TypeVar
from unittest.mock import MagicMock

from sysconf.config.system_config import RunActionsResult, SystemConfig, SystemManager
from sysconf.system.error_handler import ErrorHandler, FailureResolution
from test.system.mock_system_executor import MockSystemExecutor


FR = TypeVar('FR', bound=FailureResolution | None)


class MockSystemManager (SystemManager[FR]):
    """
    Returns the configured result from run_actions instead of planning and
    running any actions.
    """

    @classmethod
    def default(
        cls,
        result: RunActionsResult[FR] | None = None,
        old_config: SystemConfig | None = None,
        new_config: SystemConfig | None = None,
    ) -> 'MockSystemManager[FR]':
        """Create a manager, defaulting both configs to empty configs."""

        empty_config = SystemConfig.create_from_entries((), (), (), ())
        old_config = old_config or empty_config
        new_config = new_config or empty_config
        executor = MockSystemExecutor()
        error_handler: ErrorHandler[FR] = MagicMock(spec=ErrorHandler)
        result = result or RunActionsResult[FR](new_config)

        return cls(
            old_config=old_config,
            new_config=new_config,
            executor=executor,
            error_handler=error_handler,
            result=result,
        )

    def __init__(
        self,
        old_config: SystemConfig,
        new_config: SystemConfig,
        executor: MockSystemExecutor,
        error_handler: ErrorHandler[FR],
        result: RunActionsResult[FR],
    ) -> None:
        super().__init__(
            old_config=old_config,
            new_config=new_config,
            executor=executor,
            error_handler=error_handler,
        )

        self.result = result
        self.run_actions_calls = 0

    def run_actions(self) -> RunActionsResult[FR]:
        self.run_actions_calls += 1
        return self.result
