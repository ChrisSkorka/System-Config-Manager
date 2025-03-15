# pyright: strict

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace, _SubParsersAction  # pyright: ignore
from typing import Self


# Export this otherwise private type since it's needed to static type checking
SubParsersAction = _SubParsersAction


class CommandArgumentParserBuilder (ABC):
    """
    Abstract base class for building argument parsers for commands.

    Multiple mixins can be created from this class, and a command can then 
    inherit from multiple of these mixins. 

    The arguments from each mixin are added to the command's subparser in the
    order that the mixins are inherited. In this way, the command can accumulate
    and handle arguments from each mixin respectively.

    Once a command is instantiated, this system can also automatically handle 
    the parsing of the command line arguments for the respective mixin.
    """

    @classmethod
    @abstractmethod
    def add_arguments(cls, parser: ArgumentParser) -> ArgumentParser:
        """
        Add arguments to the command's subparser.

        Any arguments that this command supports should be added to this subparser.

        Args:
            parser (ArgumentParser): The subparser for the command.

        Returns:
            ArgumentParser: The subparser with added arguments.
        """
        pass  # pragma: no cover


class Command (CommandArgumentParserBuilder):
    """
    Base class for all commands.

    This class is responsible for parsing the command line arguments, 
    instantiating dependencies, and executing the command.
    """

    @classmethod
    @abstractmethod
    def create_from_arguments(cls, parsed_arguments: Namespace) -> Self:
        """Parse the arguments and create a new instance of the command."""
        pass  # pragma: no cover

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Get the name of the command.

        Returns:
            str: The name of the command.
        """
        pass  # pragma: no cover

    @classmethod
    def add_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> None:
        """
        Add a subparser for the command to the given subparsers.

        Args:
            subparsers (_SubParsersAction): The subparsers to add the subparser to.
        """
        parser = cls.get_subparser(subparsers)
        cls.add_arguments(parser)

    @classmethod
    @abstractmethod
    def get_subparser(cls, subparsers: 'SubParsersAction[ArgumentParser]') -> ArgumentParser:
        """
        Get a subparser for the command.

        This subparser should describe the command and usage but not the 
        arguments them selves.

        Args:
            subparsers (_SubParsersAction): The subparsers to add the subparser to.

        Returns:
            ArgumentParser: The subparser for the command.
        """
        pass  # pragma: no cover

    @abstractmethod
    def run(self) -> None:
        """
        Abstract method to execute the command.

        Returns:
            None
        """
        pass  # pragma: no cover
