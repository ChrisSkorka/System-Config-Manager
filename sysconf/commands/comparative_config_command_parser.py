# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import CommandArgumentParserBuilder
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.utils.config_loader import load_config_from_file
from sysconf.utils.defaults import Defaults
from sysconf.utils.file import FileReader
from sysconf.utils.path import get_validated_file_path


class ComparativeConfigCommandParser (CommandArgumentParserBuilder):
    """
    Command parser & builder for commands that compare two configurations.
    """

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:
        """
        Add all command arguments needed to find the relevant configurations.
        """

        parser.add_argument(
            'config_file',
            type=Path,
            nargs='?',
            default=None,
            help='The path to the target configuration',
        )

        parser.add_argument(
            '--last-config',
            type=Path,
            nargs='?',
            default=None,
            # todo: remove default and use configurable default path
            help='Path to the last applied configuration (default: ~/.config/config.yaml)',
        )

        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:
        """
        Parse the arguments and create a new instance that makes available the
        system manager that compares the two configurations.
        """

        defaults = Defaults()
        file_reader = FileReader()

        old_path = parsed_arguments.last_config or defaults.get_old_config_path()
        new_path = parsed_arguments.config_file or defaults.get_new_config_path()

        new_path = get_validated_file_path(
            new_path,
            '.yaml',
        )
        old_path = get_validated_file_path(
            old_path,
            '.yaml',
        )

        new_config = load_config_from_file(file_reader, new_path)
        old_config = load_config_from_file(file_reader, old_path) \
            if old_path \
            else SystemConfig({})

        system_manager = SystemManager(old_config, new_config)

        return cls(system_manager=system_manager)

    def __init__(self, system_manager: SystemManager) -> None:
        super().__init__()

        self.system_manager = system_manager
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ComparativeConfigCommandParser):
            return False
        return self.system_manager == value.system_manager

    def get_system_manager(self) -> SystemManager:
        """
        Get the system manager that compares the two configurations.

        Relation to arguments:
        - `last-config` is the old configuration
        - `config_file` is the new configuration.

        Returns:
            SystemManager: The system manager that compares the two configurations.
        """

        return self.system_manager
