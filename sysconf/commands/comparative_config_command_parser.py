# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import CommandArgumentParserBuilder
from sysconf.system.file import FileReader
from sysconf.system.path import get_validated_file_path
from sysconf.utils.context import Context
from sysconf.utils.validation import validate
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
    def create_from_arguments(
        cls,
        context: Context,
        parsed_arguments: Namespace,
    ) -> Self:
        """
        Parse the arguments and create a new instance that makes available the
        system manager that compares the two configurations.
        """

        defaults = context.get_defaults()
        file_reader = context.get_file_reader()
        config_location_reader = ConfigLocationReader(defaults, file_reader)

        old_path: Path | None = parsed_arguments.last_config or defaults.get_old_config_path()
        new_path: Path = parsed_arguments.config_file \
            or config_location_reader.get_config_path()

        current_path = defaults.get_old_config_path()
        validate(
            current_path.is_file() or not current_path.exists(),
            f'Current config path is not a file: {current_path}',
        )

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
