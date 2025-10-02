# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.utils.config_loader import load_config_from_file


class ShowCommand (Command):

    @staticmethod
    def get_name() -> str:
        return 'show'

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        return subparsers.add_parser(
            cls.get_name(),
            prog='Shows the last applied System Configuration',
            description='',
            help='',
        )

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:

        # optional positional argument
        parser.add_argument(
            'config_path',
            type=Path,
            nargs='?',
            default=Path('~/.config/system.config.yaml'),
            help='Path to the configuration file. Default: ~/.config/system.config.yaml',
        )

        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:
        return cls(config_path=parsed_arguments.config_path)

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path

    def run(self) -> None:
        print('Listing current system configuration...')

        config = load_config_from_file(self.config_path)
        print(config)
