
# pyright: strict

from pathlib import PurePath

from sysconf.utils.defaults import Defaults


class MockDefaults(Defaults):

    def __init__(
        self,
        config_dir: PurePath = PurePath('/config/'),
        old_config_path: PurePath = PurePath('/default/old.yaml'),
        new_config_path: PurePath = PurePath('/default/new.yaml'),
        config_location_path: PurePath = PurePath('/config/config'),
    ) -> None:
        self._config_dir = config_dir
        self._old_config_path = old_config_path
        self._new_config_path = new_config_path
        self._config_location_path = config_location_path

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockDefaults):
            return False

        return (
            self._config_dir == value._config_dir
            and self._old_config_path == value._old_config_path
            and self._new_config_path == value._new_config_path
            and self._config_location_path == value._config_location_path
        )

    def get_config_dir(self) -> PurePath:
        return self._config_dir

    def get_old_config_path(self) -> PurePath:
        return self._old_config_path

    def get_new_config_path(self) -> PurePath:
        return self._new_config_path

    def get_config_location_path(self) -> PurePath:
        return self._config_location_path
