# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import CommandArgumentParserBuilder
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.error_handler import ErrorHandler
from sysconf.system.executor import SystemExecutor
from sysconf.system.file import FileReader
from sysconf.system.path import get_validated_file_path
from sysconf.utils.config_loader import load_config_from_file
from sysconf.utils.defaults import Defaults


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

        old_path: Path | None = parsed_arguments.last_config or defaults.get_old_config_path()
        new_path: Path = parsed_arguments.config_file or defaults.get_new_config_path()

        current_path = defaults.get_old_config_path()
        assert current_path.is_file() or not current_path.exists(), \
            f'Current config path is not a file: {current_path}'

        new_path = get_validated_file_path(
            new_path,
            '.yaml',
        )

        # todo: allow default to not exists but not argument path
        if old_path is not None and old_path.exists():
            old_path = get_validated_file_path(
                old_path,
                '.yaml',
            )
        else:
            old_path = None

        return cls(
            old_path=old_path,
            new_path=new_path,
            file_reader=file_reader,
        )

    def __init__(
        self,
        old_path: Path | None,
        new_path: Path,
        file_reader: FileReader,

    ) -> None:
        super().__init__()

        self.old_path = old_path
        self.new_path = new_path
        self.file_reader = file_reader

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ComparativeConfigCommandParser):
            return False
        return self.old_path == value.old_path \
            and self.new_path == value.new_path \
            and self.file_reader == value.file_reader

    def get_system_manager(
        self,
        executor: SystemExecutor,
        error_handler: ErrorHandler,
    ) -> SystemManager:
        """
        Get the system manager that compares the two configurations.

        Relation to cli arguments:
        - `last-config` is the old configuration
        - `config_file` is the new configuration.
        """

        new_config = load_config_from_file(self.file_reader, self.new_path)
        old_config = load_config_from_file(self.file_reader, self.old_path) \
            if self.old_path \
            else SystemConfig.create_from_entries((), (), (), ())

        system_manager = SystemManager(
            old_config,
            new_config,
            executor,
            error_handler,
        )

        return system_manager
