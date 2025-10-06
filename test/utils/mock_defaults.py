
# pyright: strict

from sysconf.utils.defaults import Defaults
from test.utils.mock_path import MockPath


class MockDefaults(Defaults):

    def __init__(
        self,
        config_dir: MockPath = MockPath('/config/'),
        old_config_path: MockPath = MockPath('/default/old.yaml'),
        new_config_path: MockPath = MockPath('/default/new.yaml'),
    ) -> None:
        super().__init__()

        self._config_dir = config_dir
        self._old_config_path = old_config_path
        self._new_config_path = new_config_path

    def get_config_dir(self) -> MockPath:
        return self._config_dir

    def get_old_config_path(self) -> MockPath:
        return self._old_config_path

    def get_new_config_path(self) -> MockPath:
        return self._new_config_path
