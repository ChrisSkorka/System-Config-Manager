# pyright: strict

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemManager
from sysconf.system.executor import PreviewSystemExecutor, SystemExecutor
from sysconf.system.file import FileWriter
from sysconf.utils.defaults import Defaults


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

        defaults = Defaults()
        current_path = defaults.get_old_config_path()
        assert current_path.is_file() or not current_path.exists(), \
            f'Current config path is not a file: {current_path}'

        file_writer = FileWriter()
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()

        return cls(
            manager=comparative_parser.get_system_manager(),
            executor=PreviewSystemExecutor(),
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            current_path=current_path,
            file_writer=file_writer,
        )

    def __init__(
        self,
        manager: SystemManager,
        executor: SystemExecutor,
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
        current_path: Path,
        file_writer: FileWriter,
    ) -> None:
        super().__init__()

        self.manager = manager
        self.executor = executor
        self.system_config_renderer = system_config_renderer
        self.yaml_serializer = yaml_serializer
        self.current_path = current_path
        self.file_writer = file_writer

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PreviewCommand):
            return False

        return self.manager == value.manager \
            and self.executor == value.executor \
            and self.current_path == value.current_path \
            and self.file_writer == value.file_writer \
            and self.system_config_renderer == value.system_config_renderer \
            and self.yaml_serializer == value.yaml_serializer

    def run(self) -> None:
        """
        Execute the command.

        This will compare the two configurations and print the planned actions.
        """

        # Execute the actions
        current_config = self.manager.run_actions(self.executor)

        # Prepare to write the new current configuration to file but don't
        # actually write it
        # If there was a problem with the serialization, the preview command
        # should surface it insteead of the apply command failing after applying
        # changes to the system
        current_config_data = self.system_config_renderer.render_config(
            current_config,
        )
        self.yaml_serializer.get_serialized_data(current_config_data)
