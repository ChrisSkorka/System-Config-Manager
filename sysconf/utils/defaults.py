# pyright: strict

from pathlib import Path


class Defaults:
    """
    Provide default values for various configurable arguments

    Note that these defaults are not always static and may be computed from 
    things like environment variables.
    """

    def get_config_dir(self) -> Path:
        """
        Get the configuration directory.

        The config directory holds the user edited configuration files as well 
        as the history of applied configurations and any data this tool needs.
        """

        return Path('~/.config/system-config-manager/').expanduser()

    def get_old_config_path(self) -> Path:
        """
        Get the default path to the old (last applied) configuration file if it
        exists.
        """

        return self.get_config_dir() / Path('.history/current.yaml')

    def get_new_config_path(self) -> Path:
        """
        Get the default path to the new (to be applied) configuration file.
        """

        return self.get_config_dir() / Path('config.yaml')
