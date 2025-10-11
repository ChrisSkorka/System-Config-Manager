#!/usr/bin/env python3
# pyright: strict
import sys
import os

from argparse import ArgumentParser
from typing import Type
from pathlib import Path


# Add the parent directory of this file to the Python path to enable imports
current_script_path = Path(os.path.abspath(__file__))
project_root_directory = current_script_path.parent.parent
sys.path.append(str(project_root_directory))

if True:  # prevent formatter from re-ordering these imports
    from sysconf.commands.apply_command import ApplyCommand
    from sysconf.commands.command import Command
    from sysconf.commands.preview_command import PreviewCommand
    from sysconf.commands.show_command import ShowCommand

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
    }

    for commandCls in commands.values():
        subparser = commandCls.get_subparser(subparsers)
        commandCls.add_arguments(subparser)

    parsed_args = parser.parse_args()
    commands_name = parsed_args.command

    if commands_name is None:
        parser.print_help()
        return

    command: Command = commands[commands_name].create_from_arguments(
        parsed_args)
    command.run()


if __name__ == '__main__':
    main()
