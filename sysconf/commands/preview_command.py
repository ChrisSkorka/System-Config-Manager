# pyright: strict

from argparse import ArgumentParser, Namespace
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemManager
from sysconf.system.executor import PreviewSystemExecutor, SystemExecutor


class PreviewCommand (Command):

    @staticmethod
    def get_name() -> str:
        """Get the name if this subcommand."""

        return 'preview'

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        """
        Get a subparser for the command, add_arguments will add all the
        arguments we need.
        """

        return subparsers.add_parser(
            cls.get_name(),
            prog='Preview planned actions without executing',
            description='Compare the current system configuration with the '
            + 'target configuration and generate (but not execute) the '
            + 'necessary commands.',
            help='',
        )

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:
        """
        Add all command arguments needed to find the relevant configurations.
        """

        ComparativeConfigCommandParser.add_arguments(parser)

        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:
        """
        Validate the arguments and create a ready to run instance from those
        arguments.
        """

        comparative_parser = ComparativeConfigCommandParser.create_from_arguments(
            parsed_arguments)

        return cls(
            manager=comparative_parser.get_system_manager(),
            executor=PreviewSystemExecutor(),
        )

    def __init__(self, manager: SystemManager, executor: SystemExecutor) -> None:
        super().__init__()

        self.manager = manager
        self.executor = executor

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PreviewCommand):
            return False

        return self.manager == value.manager \
            and self.executor == value.executor

    def run(self) -> None:
        """
        Execute the command.

        This will compare the two configurations and print the planned actions.
        """

        current_config = self.manager.run_actions(self.executor)
        system_config_renderer = SystemConfigRenderer()
        current_config_data = system_config_renderer.render_config(
            current_config,
        )
        yaml_string = YamlSerializer().get_serialized_data(current_config_data)
        print(yaml_string)
