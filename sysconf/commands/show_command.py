# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import PurePath
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.system.file import FileReader
from sysconf.utils.context import Context
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
            type=PurePath,
            nargs='?',
            default=None,
            help='Path to the configuration file. (default: ~/.config/config.yaml)',
        )

        return parser

    @classmethod
    def create_from_arguments(
        cls,
        context: Context,
        parsed_arguments: Namespace,
    ) -> Self:

        file_reader = context.get_file_reader()
        path_service = context.get_path_service()
        defaults = Defaults(path_service)

        config_path = (
            parsed_arguments.config_path
            or defaults.get_old_config_path()
        )

        config_path = path_service.get_validated_file_path(
            config_path,
            '.yaml',
        )

        return cls(config_path=config_path, file_reader=file_reader)

    def __init__(
        self,
        config_path: PurePath,
        file_reader: FileReader,
    ) -> None:
        super().__init__()

        self.config_path = config_path
        self.file_reader = file_reader

    def run(self) -> None:
        print('Listing current system configuration...')

        serialized_config = self.file_reader \
            .get_file_contents(self.config_path)

        print(serialized_config)
