# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemManager
from sysconf.system.error_handler import PromptUserErrorHandler
from sysconf.system.executor import CommandException, LiveSystemExecutor
from sysconf.system.file import FileWriter
from sysconf.utils.defaults import Defaults


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
        system_manager = comparative_parser.get_system_manager(
            executor=LiveSystemExecutor(),
            error_handler=PromptUserErrorHandler(CommandException),
        )

        defaults = Defaults()
        current_path = defaults.get_old_config_path()
        assert current_path.is_file() or not current_path.exists(), \
            f'Current config path is not a file: {current_path}'

        file_writer = FileWriter()
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()

        return cls(
            manager=system_manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            current_path=current_path,
            file_writer=file_writer,
        )

    def __init__(
        self,
        manager: SystemManager,
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
        current_path: Path,
        file_writer: FileWriter,
    ) -> None:
        super().__init__()

        self.manager = manager
        self.system_config_renderer = system_config_renderer
        self.yaml_serializer = yaml_serializer
        self.current_path = current_path
        self.file_writer = file_writer

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ApplyCommand):
            return False

        return self.manager == value.manager \
            and self.current_path == value.current_path \
            and self.file_writer == value.file_writer \
            and self.system_config_renderer == value.system_config_renderer \
            and self.yaml_serializer == value.yaml_serializer

    def run(self) -> None:
        """
        Execute the command.

        This will compare the two configurations and execute the required
        actions, and update the current configuration file with the changes that
        were successfully applied.

        Incase an action fails, the user will be prompted if they want to
        continue with the remaining actions or abort.
        If the user chooses to continue, that action will not be commited to the
        current configuration file.
        """

        # Execute the actions
        current_config = self.manager.run_actions()

        # Write the new current configuration
        current_config_data = self.system_config_renderer.render_config(
            current_config,
        )
        yaml_string = self.yaml_serializer.get_serialized_data(
            current_config_data,
        )
        try:
            self.file_writer.write_file_contents(
                self.current_path,
                yaml_string,
            )
        except Exception as e:
            print('Current System Configuration:')
            print(yaml_string)
            print()  # Empty line

            print('The changes were successfully applied to the system, '
                  + 'but an error occurred while writing the updated current configuration file:',
            )
            print(str(e))
            print(
                f'Please copy the above configuration and save it to {self.current_path}.',
            )
