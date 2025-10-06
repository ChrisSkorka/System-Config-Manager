
# pyright: strict

from typing import Callable, Iterable, Sequence
from unittest.mock import MagicMock
from sysconf.config.domains import DomainAction
from sysconf.config.system_config import SystemConfig, SystemManager
from test.domains.mock_domain_action import MockDomainAction
from test.system.mock_system_config import MockSystemConfig


class MockSystemManager (SystemManager):

    def __init__(
        self,
        old_config: SystemConfig,
        new_config: SystemConfig,
        get_actions: Sequence[DomainAction] | None = None,
    ) -> None:
        super().__init__(old_config=old_config, new_config=new_config)
        get_actions = get_actions or []

        self.get_actions: (  # type: ignore
            MagicMock | Callable[[SystemManager], Iterable[MockDomainAction]]
        ) = MagicMock(return_value=get_actions)

    @classmethod
    def default(
        cls,
        old_config: SystemConfig | None = None,
        new_config: SystemConfig | None = None,
        get_actions: Sequence[DomainAction] | None = None,
    ) -> 'MockSystemManager':

        old_config = old_config or MockSystemConfig.default()
        new_config = new_config or MockSystemConfig.default()
        get_actions = get_actions or []

        return cls(old_config=old_config, new_config=new_config, get_actions=get_actions)
