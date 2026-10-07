# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import PurePath
from typing import Self

from sysconf.commands.command import CommandArgumentParserBuilder
from sysconf.system.file import FileReader
from sysconf.utils.context import Context
from sysconf.utils.config_location import ConfigLocationReader


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
            type=PurePath,
            nargs='?',
            default=None,
            help='The path to the target configuration',
        )

        parser.add_argument(
            '--last-config',
            type=PurePath,
            nargs='?',
            default=None,
            help='Path to the last applied configuration (default: ~/.config/config.yaml)',
        )

        return parser

    @classmethod
    def create_from_arguments(
        cls,
        context: Context,
        parsed_arguments: Namespace,
    ) -> Self:
        """
        Parse the arguments and create a new instance that makes available the
        old and new configurations.
        """

        defaults = context.get_defaults()
        file_reader = context.get_file_reader()
        path_service = context.get_path_service()
        config_location_reader = ConfigLocationReader(
            defaults,
            file_reader,
            path_service,
        )

        arg_last_config_path: PurePath | None = parsed_arguments.last_config
        default_last_config_path: PurePath = defaults.get_old_config_path()

        arg_config_path: PurePath | None = parsed_arguments.config_file
        is_config_file_explicit = arg_config_path is not None

        # argument or default path for the old config path
        old_path: PurePath
        new_path: PurePath

        # if a last config path is given, it must exists & be valid,
        # otherwise use the default,
        # default has to either be non-existent or valid
        if arg_last_config_path is not None:
            old_path = path_service.get_validated_file_path(
                arg_last_config_path,
                '.yaml',
            )
        else:
            old_path = default_last_config_path

        is_old_path_existing = path_service.exists(old_path)
        if is_old_path_existing:
            old_path = path_service.get_validated_file_path(old_path, '.yaml')

        if arg_config_path is not None:
            new_path = arg_config_path
        else:
            new_path = config_location_reader.get_config_path()
        new_path = path_service.get_validated_file_path(new_path, '.yaml')

        return cls(
            old_path=old_path,
            new_path=new_path,
            is_config_file_explicit=is_config_file_explicit,
            file_reader=file_reader,
        )

    def __init__(
        self,
        old_path: PurePath,
        new_path: PurePath,
        is_config_file_explicit: bool,
        file_reader: FileReader,

    ) -> None:
        super().__init__()

        self.old_path = old_path
        self.new_path = new_path
        self.is_config_file_explicit = is_config_file_explicit
        self.file_reader = file_reader

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ComparativeConfigCommandParser):
            return False
        return (
            self.old_path == value.old_path
            and self.new_path == value.new_path
            and self.is_config_file_explicit == value.is_config_file_explicit
            and self.file_reader == value.file_reader
        )
