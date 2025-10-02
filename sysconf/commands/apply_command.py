# pyright: strict

from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.executor import LiveSystemExecutor, PreviewSystemExecutor, SystemExecutor
from sysconf.utils.config_loader import load_config_from_file


class AbstractApplyCommand (Command):

    @abstractmethod
    def getSystemExecutor(self) -> SystemExecutor:
        """
        Get the system executor to use for executing the command.

        Returns:
            SystemExecutor: The system executor to use.
        """
        pass

    @classmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        return subparsers.add_parser(
            cls.get_name(),
            prog='Preview planned actions without executing',
            description='',
            help='',
        )

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:

        parser.add_argument(
            'config_file',
            type=Path,
            help='The path to the target configuration',
        )

        parser.add_argument(
            '--last-config',
            type=Path,
            default=Path('./config/config.yaml'),
            help='Path to the last applied configuration (default: ./config/config.yaml)',
        )

        return parser

    @classmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:

        path = parsed_arguments.config_file
        assert isinstance(path, Path)
        cls.validate_config_path(path)

        old_path = parsed_arguments.last_config
        assert isinstance(old_path, Path)
        cls.validate_config_path(old_path)

        return cls(new_path=path, old_path=old_path)

    @staticmethod
    def validate_config_path(path: Path) -> None:
        assert path.exists(), f'File {path} does not exist'
        assert path.is_file(), f'Path {path} is not a file'
        assert path.suffix == '.yaml', f'File {path} is not a YAML file'

    def __init__(self, new_path: Path, old_path: Path | None):
        self.new_path = new_path
        self.old_path = old_path

        self.new_config = load_config_from_file(new_path)
        self.old_config = load_config_from_file(
            old_path) if old_path else SystemConfig({})

    def run(self) -> None:
        executor = self.getSystemExecutor()
        manager = SystemManager(self.old_config, self.new_config)
        actions = manager.get_actions()

        if not actions:
            print('# No changes required.')
            return

        for a in actions:
            print(f'# {a.get_description()}')
            a.run(executor)


class PreviewCommand (AbstractApplyCommand):

    @staticmethod
    def get_name() -> str:
        return 'preview'

    def getSystemExecutor(self) -> SystemExecutor:
        return PreviewSystemExecutor()


class ApplyCommand (AbstractApplyCommand):

    @staticmethod
    def get_name() -> str:
        return 'apply'

    def getSystemExecutor(self) -> SystemExecutor:
        return LiveSystemExecutor()
