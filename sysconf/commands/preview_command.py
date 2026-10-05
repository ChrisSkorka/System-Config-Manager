# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemManager
from sysconf.system.error_handler import FailingErrorHandler
from sysconf.system.executor import PreviewSystemExecutor
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.context import Context


class PreviewCommand (Command):

    @staticmethod
    def get_name() -> str:
        """Get the name of this subcommand."""

        return 'preview'

    @classmethod
    def get_subparser(cls, subparsers: SubParsersAction[ArgumentParser]) -> ArgumentParser:
        """
        Get a subparser for the command, add_arguments will add all the
        arguments we need.
        """

        return subparsers.add_parser(
            cls.get_name(),
            prog='sysconf ' + cls.get_name(),
            description='Compare the current system configuration with the '
            'target configuration and generate (but not execute) the '
            'differential commands required to bring the system to the '
            'desired state.',
            help='Preview planned actions without executing',
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

        return cls.create_from_context(
            context=context,
            old_path=old_path,
            new_path=new_path,
        )

    @classmethod
    def create_from_context(
        cls,
        context: Context,
        old_path: Path,
        new_path: Path,
    ) -> Self:
        """
        Create a new instance of the command from the given context and
        system manager.
        """

        file_reader = context.get_file_reader()

        config_reader = ConfigReader(file_reader)

        old_config = config_reader.load_or_default(old_path)
        new_config = config_reader.load(new_path)

        executor = PreviewSystemExecutor()
        error_handler = FailingErrorHandler()
        system_manager = SystemManager(
            old_config=old_config,
            new_config=new_config,
            executor=executor,
            error_handler=error_handler,
        )
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()

        return cls(
            manager=system_manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
        )

    def __init__(
        self,
        manager: SystemManager[None],
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
    ) -> None:
        super().__init__()

        self.manager = manager
        self.system_config_renderer = system_config_renderer
        self.yaml_serializer = yaml_serializer

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PreviewCommand):
            return False

        return self.manager == value.manager \
            and self.system_config_renderer == value.system_config_renderer \
            and self.yaml_serializer == value.yaml_serializer

    def run(self) -> None:
        """
        Execute the command.

        This will compare the two configurations and print the planned actions.
        """

        # Execute the actions
        result = self.manager.run_actions()

        # Prepare to write the new current configuration to file but don't
        # actually write it
        # If there was a problem with the serialization, the preview command
        # should surface it insteead of the apply command failing after applying
        # changes to the system
        current_config_data = self.system_config_renderer.render_config(
            result.system_config,
        )
        self.yaml_serializer.get_serialized_data(current_config_data)
