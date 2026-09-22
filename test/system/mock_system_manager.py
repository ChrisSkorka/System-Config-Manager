# pyright: strict

from typing import Iterable, Sequence
from unittest.mock import MagicMock
from sysconf.config.domains import DomainAction, NoDomainAction
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.error_handler import ErrorHandler
from test.system.mock_system_executor import MockSystemExecutor


class MockSystemManager (SystemManager):

    def __init__(
        self,
        old_config: SystemConfig,
        new_config: SystemConfig,
        get_actions: Sequence[DomainAction] | None = None,
    ) -> None:
        mock_error_handler: ErrorHandler = MagicMock(spec=ErrorHandler)

        super().__init__(
            old_config=old_config,
            new_config=new_config,
            executor=MockSystemExecutor(),
            error_handler=mock_error_handler,
        )

        self._actions: list[DomainAction] = list(get_actions or [])

    def get_domain_actions(self) -> Iterable[DomainAction]:
        return self._actions

    def run_actions(self) -> SystemConfig:
        actions = list(self.get_domain_actions())
        has_non_noop = any(not isinstance(a, NoDomainAction) for a in actions)
        if not has_non_noop:
            print('# No changes required.')
            return self.new_config
        for action in actions:
            if not isinstance(action, NoDomainAction):
                print(f'# {action.get_description()}')
                action.run(self.executor)
        return self.new_config

    @classmethod
    def default(
        cls,
        old_config: SystemConfig | None = None,
        new_config: SystemConfig | None = None,
        get_actions: Sequence[DomainAction] | None = None,
    ) -> 'MockSystemManager':

        old_config = old_config or SystemConfig.create_from_entries(before_actions=(), after_actions=(), config_entries=(), user_domains=())
        new_config = new_config or SystemConfig.create_from_entries(before_actions=(), after_actions=(), config_entries=(), user_domains=())
        get_actions = get_actions or []

        return cls(old_config=old_config, new_config=new_config, get_actions=get_actions)
