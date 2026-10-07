#!/usr/bin/env python3
# pyright: strict
import sys
import os

from argparse import ArgumentParser
from typing import Type
from pathlib import Path

from sysconf.utils.context import Context


# Add the parent directory of this file to the Python path to enable imports
current_script_path = Path(os.path.abspath(__file__))
project_root_directory = current_script_path.parent.parent
sys.path.append(str(project_root_directory))

if True:  # prevent formatter from re-ordering these imports
    from sysconf.commands.apply_command import ApplyCommand
    from sysconf.commands.command import Command
    from sysconf.commands.edit_command import EditCommand
    from sysconf.commands.preview_command import PreviewCommand
    from sysconf.commands.show_command import ShowCommand
    from sysconf.system.executor import LiveSystemExecutor
    from sysconf.system.file import FileReader, FileWriter
    from sysconf.utils.defaults import Defaults
    from sysconf.utils.validation import ValidationError

"""
This is the entry point for the linux configuration manager program. It parses 
the command line arguments, initializes the commands and runs the command.

run `cli.py --help` for instructions
"""


def main() -> None:

    parser = ArgumentParser(
        prog='System Config Manager CLI',
        description='Tool suit to create, manage and apply system configurations from config files.',
    )
    subparsers = parser.add_subparsers(
        help='available commands',
        dest='command',
    )

    commands: dict[str, Type[Command]] = {
        ShowCommand.get_name(): ShowCommand,
        PreviewCommand.get_name(): PreviewCommand,
        ApplyCommand.get_name(): ApplyCommand,
        EditCommand.get_name(): EditCommand,
    }

    for commandCls in commands.values():
        subparser = commandCls.get_subparser(subparsers)
        commandCls.add_arguments(subparser)

    parsed_args = parser.parse_args()
    commands_name = parsed_args.command

    if commands_name is None:
        parser.print_help()
        return

    defaults = Defaults()
    file_reader = FileReader()
    file_writer = FileWriter()
    system_executor = LiveSystemExecutor()
    context = Context(
        defaults=defaults,
        file_reader=file_reader,
        file_writer=file_writer,
        system_executor=system_executor,
    )

    try:
        command: Command | None = commands[commands_name].create_from_arguments(
            context,
            parsed_args,
        )
        while command is not None:
            command = command.run()
    except ValidationError as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
