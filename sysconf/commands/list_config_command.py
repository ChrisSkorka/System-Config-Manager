# pyright: strict

from argparse import ArgumentParser, Namespace
from typing import Self

from sysconf.commands.command import Command, SubParsersAction

class ListConfigCommand (Command):

    @staticmethod
    def get_name() -> str:
        return 'list-config'

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        return subparsers.add_parser(
            cls.get_name(),
            prog='List Current System Configuration',
            description='',
            help='',
        )

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:
        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:
        return cls()

    def run(self) -> None:
        print('Listing current system configuration...')