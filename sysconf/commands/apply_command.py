# pyright: strict

from argparse import ArgumentParser, Namespace
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.system_config import SystemManager
from sysconf.system.executor import CommandException, LiveSystemExecutor, SystemExecutor


class ApplyCommand (Command):

    @staticmethod
    def get_name() -> str:
        """Get the name if this subcommand."""

        return 'apply'

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        """
        Get a subparser for the command, add_arguments will add all the
        arguments we need.
        """

        return subparsers.add_parser(
            cls.get_name(),
            prog='Apply the configuration to the system',
            description='Compare the current system configuration with the target configuration and execute the necessary commands.',
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
            parsed_arguments,
        )

        return cls(
            manager=comparative_parser.get_system_manager(),
            executor=LiveSystemExecutor(),
        )

    def __init__(self, manager: SystemManager, executor: SystemExecutor) -> None:
        super().__init__()

        self.manager = manager
        self.executor = executor

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ApplyCommand):
            return False

        return self.manager == value.manager \
            and self.executor == value.executor

    def run(self) -> None:
        """
        Execute the command.

        This will compare the two configurations and execute the required
        actions.

        Incase an action fails, the user will be prompted if they want to
        continue with the remaining actions or abort.
        """

        actions = self.manager.get_actions()

        if not actions:
            print('# No changes required.')
            return

        for a in actions:
            print(f'# {a.get_description()}')

            try:
                a.run(self.executor)
            except CommandException as e:
                print(f'An error occurred while executing the command:')
                print(e.cmdline)
                print(
                    f'Process exited with code {e.process.returncode}, see output above.',
                )

                should_continue = self.get_user_confirmation(
                    'Do you want to continue with the remaining tasks?',
                )
                if not should_continue:
                    return
                else:
                    continue

    def get_user_confirmation(self, prompt: str) -> bool:
        """
        Promt the user for a yes/no confirmation to a prompt.

        Notes:
        - Accepts 'y', 'yes', 'n', 'no' (case insensitive)
        - Allows up to 3 attempts
        - Defaults to false ('no') if no valid input is given in the 3 attempts
        """

        for _ in range(3):  # allow up to 3 attempts
            user_input = input(f'{prompt} (y/n): ').strip().lower()
            if user_input in ('y', 'yes'):
                return True
            elif user_input in ('n', 'no', ''):
                return False

        return False
