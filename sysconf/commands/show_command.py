# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.system.file import FileReader
from sysconf.system.path import get_validated_file_path
from sysconf.utils.config_loader import load_config_from_file
from sysconf.utils.defaults import Defaults


class ShowCommand (Command):

    @staticmethod
    def get_name() -> str:
        return 'show'

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        return subparsers.add_parser(
            cls.get_name(),
            prog='sysconf ' + cls.get_name(),
            description='Prints the last applied System Configuration',
            help='Prints the last applied System Configuration',
        )

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:

        parser.add_argument(
            'config_path',
            type=Path,
            nargs='?',
            default=None,
            help='Path to the configuration file. (default: ~/.config/config.yaml)',
        )

        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:

        defaults = Defaults()

        config_path = parsed_arguments.config_path \
            or defaults.get_old_config_path()

        config_path = get_validated_file_path(
            config_path,
            '.yaml',
        )

        return cls(config_path=config_path)

    def __init__(self, config_path: Path) -> None:
        super().__init__()

        self.config_path = config_path
        self.file_reader = FileReader()

    def run(self) -> None:
        print('Listing current system configuration...')

        config = load_config_from_file(self.file_reader, self.config_path)
        print(config)
