# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemManager
from sysconf.system.error_handler import PromptUserErrorHandler
from sysconf.system.executor import CommandException
from sysconf.utils.choice_prompt import ChoicePromptOptionEnum
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.context import Context
from sysconf.utils.validation import validate
from sysconf.utils.config_location import ConfigLocationWriter
from sysconf.utils.config_writer import ConfigWriter

if TYPE_CHECKING:
    from sysconf.commands.edit_command import EditCommand


class ApplyFailureResolution(ChoicePromptOptionEnum):

    ABORT = ('a', 'Abort')
    EDIT = ('e', 'Edit config')


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
    def create_from_arguments(
        cls,
        context: Context,
        parsed_arguments: Namespace,
    ) -> Self:
        """
        Validate the arguments and create a ready to run instance from those
        arguments.
        """

        comparative_parser = ComparativeConfigCommandParser.create_from_arguments(
            context=context,
            parsed_arguments=parsed_arguments,
        )
        old_path = comparative_parser.old_path
        new_path = comparative_parser.new_path
        should_override_config_path = comparative_parser.is_config_file_explicit

        return cls.create_from_context(
            context=context,
            old_path=old_path,
            new_path=new_path,
            should_override_config_path=should_override_config_path,
        )

    @classmethod
    def create_from_context(
        cls,
        context: Context,
        old_path: Path,
        new_path: Path,
        should_override_config_path: bool,
    ) -> Self:
        """
        Create an instance of the command from the given context.
        """

        defaults = context.get_defaults()
        executor = context.get_system_executor()
        file_reader = context.get_file_reader()
        file_writer = context.get_file_writer()

        config_reader = ConfigReader(file_reader)

        old_config = config_reader.load_or_default(old_path)
        new_config = config_reader.load(new_path)

        error_handler = PromptUserErrorHandler[ApplyFailureResolution](
            CommandException,
            failure_resolutions=(
                ApplyFailureResolution.ABORT,
                ApplyFailureResolution.EDIT,
            ),
        )
        system_manager = SystemManager(
            old_config=old_config,
            new_config=new_config,
            executor=executor,
            error_handler=error_handler,
        )

        current_path = defaults.get_old_config_path()
        validate(
            current_path.is_file() or not current_path.exists(),
            f'Current config path is not a file: {current_path}',
        )

        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        config_writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )
        config_location_writer = ConfigLocationWriter(
            defaults,
            file_reader,
            file_writer,
        )

        def edit_command_factory() -> 'EditCommand':
            from sysconf.commands.edit_command import EditCommand

            edit_command = EditCommand.create_from_context(
                context=context,
                old_path=old_path,
                new_path=new_path,
            )
            return edit_command

        return cls(
            manager=system_manager,
            current_path=current_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=should_override_config_path,
            edit_command_factory=edit_command_factory,
        )

    def __init__(
        self,
        manager: SystemManager[ApplyFailureResolution],
        current_path: Path,
        new_path: Path,
        config_writer: ConfigWriter,
        config_location_writer: ConfigLocationWriter,
        should_override_config_path: bool,
        edit_command_factory: 'Callable[[], EditCommand]',
    ) -> None:
        super().__init__()

        self.manager = manager
        self.current_path = current_path
        self.new_path = new_path
        self.config_writer = config_writer
        self.config_location_writer = config_location_writer
        self.should_override_config_path = should_override_config_path
        self.edit_command_factory = edit_command_factory

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ApplyCommand):
            return False

        return self.manager == value.manager \
            and self.current_path == value.current_path \
            and self.new_path == value.new_path \
            and self.config_writer == value.config_writer \
            and self.config_location_writer == value.config_location_writer \
            and self.should_override_config_path == value.should_override_config_path
        # excluded:
        # and self.edit_command_factory == value.edit_command_factory

    def run(self) -> Command | None:
        """
        Execute the command.

        This will record where the configuration came from, compare the two
        configurations and execute the required actions, and update the current
        configuration file with the changes that were successfully applied.

        The config location is recorded before any action runs so that a config
        that fails part way through still leaves the location recorded for the
        next invocation.

        Incase an action fails, the user will be prompted if they want to
        continue with the remaining actions, abort, or edit the config.
        If the user chooses to continue, that action will not be commited to the
        current configuration file.
        """

        # Record where the configuration we are about to apply came from
        if self.should_override_config_path:
            is_path_saved = self.config_location_writer \
                .record_config_path(self.new_path)

            if is_path_saved:
                print(
                    f'Saved "{self.new_path}" as your config location',
                )

        # Execute the actions
        result = self.manager.run_actions()

        # Write the new current configuration
        try:
            self.config_writer.write(result.system_config, self.current_path)
        except Exception as e:
            current_config_data = self.config_writer.system_config_renderer.render_config(
                result.system_config,
            )
            yaml_string = self.config_writer.yaml_serializer.get_serialized_data(
                current_config_data,
            )

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

        match result.failure_resolution:
            case ApplyFailureResolution.EDIT:
                return self.edit_command_factory()
            case ApplyFailureResolution.ABORT | None:
                return None
