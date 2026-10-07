# pyright: strict

from pathlib import PurePath

from sysconf.system.path_service import PathService


class Defaults:
    """
    Provide default values for various configurable arguments

    Note that these defaults are not always static and may be computed from 
    things like environment variables.
    """

    def __init__(self, path_service: PathService) -> None:
        self.path_service = path_service

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Defaults):
            return False

        return self.path_service == value.path_service

    def get_config_dir(self) -> PurePath:
        """
        Get the configuration directory.

        The config directory holds the user edited configuration files as well 
        as the history of applied configurations and any data this tool needs.
        """

        config_dir = PurePath('~/.config/system-config-manager/')

        return self.path_service.expand_user(config_dir)

    def get_old_config_path(self) -> PurePath:
        """
        Get the default path to the old (last applied) configuration file if it
        exists.
        """

        return self.get_config_dir() / PurePath('.history/current.yaml')

    def get_config_location_path(self) -> PurePath:
        """
        Get the path that records where the user's source of truth config lives.

        This path is either a file whose contents are the path to the
        configuration file, or a directory holding the configuration itself.
        """

        return self.get_config_dir() / PurePath('config')

    def get_new_config_path(self) -> PurePath:
        """
        Get the default path to the new (to be applied) configuration file.

        This is the path used when the config location is a directory.
        """

        return self.get_config_location_path() / PurePath('config.yaml')
