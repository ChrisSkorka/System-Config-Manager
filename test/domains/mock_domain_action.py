# pyright: strict

from unittest.mock import MagicMock
from sysconf.config.domains import DomainAction
from sysconf.system.executor import SystemExecutor


class MockDomainAction(DomainAction):

    def __init__(self, description: str) -> None:
        self.description = description

        self.get_description = MagicMock(return_value=description)
        self.run = MagicMock()

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockDomainAction):
            return False
        
        return self.description == value.description
    
    def get_description(self) -> str: # pyright: ignore
        pass

    def run(self, executor: SystemExecutor) -> None:
        pass
