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
from sysconf.system.file import FileReader, FileWriter
from sysconf.utils.choice_prompt import ChoicePromptOptionEnum
from sysconf.utils.validation import validate
from sysconf.utils.config_location import ConfigLocationWriter
from sysconf.utils.defaults import Defaults


class ApplyFailureResolution(ChoicePromptOptionEnum):

    ABORT = ('a', 'Abort')


class ApplyCommand (Command):

    @staticmethod
    def get_name() -> str:
        """Get the name of this subcommand."""

        return 'apply'

    @classmethod
    def get_subparser(cls, subparsers: SubParsersAction[ArgumentParser]) -> ArgumentParser:
        """
        Get a subparser for the command, add_arguments will add all the
        arguments we need.
        """

        return subparsers.add_parser(
            cls.get_name(),
            prog='sysconf ' + cls.get_name(),
            help='Apply the configuration to the system',
            description='Compare the current system configuration with the '
            'target configuration and execute the differential commands to '
            'bring the system to the desired state.',
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
        error_handler = PromptUserErrorHandler[ApplyFailureResolution](
            CommandException,
            failure_resolutions=(ApplyFailureResolution.ABORT,),
        )
        system_manager = comparative_parser.get_system_manager(
            executor=LiveSystemExecutor(),
            error_handler=error_handler,
        )

        defaults = Defaults()
        current_path = defaults.get_old_config_path()
        validate(
            current_path.is_file() or not current_path.exists(),
            f'Current config path is not a file: {current_path}',
        )

        file_writer = FileWriter()
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        config_location_writer = ConfigLocationWriter(
            defaults,
            FileReader(),
            file_writer,
        )

        return cls(
            manager=system_manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            current_path=current_path,
            file_writer=file_writer,
            config_location_writer=config_location_writer,
            config_path_argument=parsed_arguments.config_file,
        )

    def __init__(
        self,
        manager: SystemManager[ApplyFailureResolution],
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
        current_path: Path,
        file_writer: FileWriter,
        config_location_writer: ConfigLocationWriter,
        config_path_argument: Path | None,
    ) -> None:
        super().__init__()

        self.manager = manager
        self.system_config_renderer = system_config_renderer
        self.yaml_serializer = yaml_serializer
        self.current_path = current_path
        self.file_writer = file_writer
        self.config_location_writer = config_location_writer
        self.config_path_argument = config_path_argument

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ApplyCommand):
            return False

        return self.manager == value.manager \
            and self.current_path == value.current_path \
            and self.file_writer == value.file_writer \
            and self.system_config_renderer == value.system_config_renderer \
            and self.yaml_serializer == value.yaml_serializer \
            and self.config_location_writer == value.config_location_writer \
            and self.config_path_argument == value.config_path_argument

    def run(self) -> None:
        """
        Execute the command.

        This will record where the configuration came from, compare the two
        configurations and execute the required actions, and update the current
        configuration file with the changes that were successfully applied.

        The config location is recorded before any action runs so that a config
        that fails part way through still leaves the location recorded for the
        next invocation.

        Incase an action fails, the user will be prompted if they want to
        continue with the remaining actions or abort.
        If the user chooses to continue, that action will not be commited to the
        current configuration file.
        """

        # Record where the configuration we are about to apply came from
        if self.config_path_argument is not None:
            is_path_saved = self.config_location_writer \
                .record_config_path(self.config_path_argument)

            if is_path_saved:
                print(
                    f'Saved "{self.config_path_argument}" as your config location',
                )

        # Execute the actions
        result = self.manager.run_actions()

        # Write the new current configuration
        current_config_data = self.system_config_renderer.render_config(
            result.system_config,
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
