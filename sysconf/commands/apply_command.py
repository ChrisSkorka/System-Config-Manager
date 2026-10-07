# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import PurePath
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
from sysconf.utils.config_location import ConfigLocationWriter
from sysconf.utils.config_writer import ConfigWriter
from sysconf.utils.context import Context
from sysconf.utils.defaults import Defaults

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
        old_path: PurePath,
        new_path: PurePath,
        should_override_config_path: bool,
    ) -> Self:
        """
        Create an instance of the command from the given context.
        """

        executor = context.get_system_executor()
        file_reader = context.get_file_reader()
        path_service = context.get_path_service()
        defaults = Defaults(path_service)
        file_writer = context.get_file_writer()

        system_config_renderer = SystemConfigRenderer()
        config_writer = ConfigWriter(
            system_config_renderer=system_config_renderer,
            yaml_serializer=YamlSerializer(),
            file_writer=file_writer,
        )
        config_location_writer = ConfigLocationWriter(
            defaults=defaults,
            file_reader=file_reader,
            file_writer=file_writer,
            path_service=path_service,
        )
        config_reader = ConfigReader(file_reader, path_service)

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
            old_path=old_path,
            new_path=new_path,
            config_writer=config_writer,
            config_location_writer=config_location_writer,
            should_override_config_path=should_override_config_path,
            edit_command_factory=edit_command_factory,
        )

    def __init__(
        self,
        manager: SystemManager[ApplyFailureResolution],
        old_path: PurePath,
        new_path: PurePath,
        config_writer: ConfigWriter,
        config_location_writer: ConfigLocationWriter,
        should_override_config_path: bool,
        edit_command_factory: 'Callable[[], EditCommand]',
    ) -> None:
        super().__init__()

        self.manager = manager
        self.old_path = old_path
        self.new_path = new_path
        self.config_writer = config_writer
        self.config_location_writer = config_location_writer
        self.should_override_config_path = should_override_config_path
        self.edit_command_factory = edit_command_factory

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ApplyCommand):
            return False

        return (
            self.manager == value.manager
            and self.old_path == value.old_path
            and self.new_path == value.new_path
            and self.config_writer == value.config_writer
            and self.config_location_writer == value.config_location_writer
            and self.should_override_config_path == value.should_override_config_path
        )
        # exclude:
        # and self.edit_command_factory == value.edit_command_factory

    def run(self) -> Command | None:
        """
        Execute the command.

        1. record config path
        2. run system commands to update the system
        3. record the updated configuration
        4. on failure, prompt the user for how to proceed
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
            self.config_writer.write(result.system_config, self.old_path)
        except Exception as e:
            current_path = self.old_path
            config_data = self.config_writer.system_config_renderer.render_config(
                result.system_config,
            )
            config_yaml = self.config_writer.yaml_serializer.get_serialized_data(
                config_data,
            )

            print('Failed to write current system configuration to file!')
            print(str(e))
            print()  # Empty line
            print(
                'The changes were successfully applied to the system, '
                + 'but an error occurred while writing the updated configuration file.',
            )
            print()  # Empty line
            print('Current System Configuration:')
            print('```')
            print(config_yaml)
            print('```')
            print()  # Empty line
            print(
                f'Please copy the above configuration and save it to {current_path}.',
            )

        match result.failure_resolution:
            case ApplyFailureResolution.EDIT:
                return self.edit_command_factory()
            case ApplyFailureResolution.ABORT:
                return None
            case _:
                return None
