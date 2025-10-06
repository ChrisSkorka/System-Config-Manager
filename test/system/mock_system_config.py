# pyright: strict

from sysconf.config.domains import DomainConfig
from sysconf.config.system_config import SystemConfig
from test.domains.mock_domain_config import MockDomainConfig


class MockSystemConfig(SystemConfig):

    @classmethod
    def default(
        cls, 
        data: dict[str, DomainConfig] | None = None,
    ) -> 'MockSystemConfig':

        data = data or {
            'domain': MockDomainConfig.default(),
        }

        return cls(data=data)