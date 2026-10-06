# pyright: strict

import shutil
import sys

from argparse import ArgumentParser, Namespace  # , RawDescriptionHelpFormatter
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Self

from sysconf.commands.command import Command, SubParsersAction
from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.system.editor import EditResult, EditorLauncher, EditorResolver
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.context import Context
from sysconf.utils.validation import ValidationError

if TYPE_CHECKING:
    from sysconf.commands.apply_command import ApplyCommand
    from sysconf.commands.preview_command import PreviewCommand


class ApplyChoice (Enum):
    """The user's choice when asked whether to apply the edited config."""

    APPLY = auto()
    EDIT = auto()
    EXIT = auto()


class EditCommand (Command):
    """
    Open the configuration in an editor, then ask the user whether to apply
    it, preview its actions first, edit it again, or exit without applying it
    once the editor exits.

    If the edited configuration is invalid, or an action fails while applying
    it, the user can choose to edit the configuration again. After a failed
    action, the changes applied so far are recorded before the editor is opened
    again, so the next attempt continues from the partially applied state.
    """

    @staticmethod
    def get_name() -> str:
        """Get the name of this subcommand."""

        return 'edit'

    @classmethod
    def get_subparser(cls, subparsers: SubParsersAction[ArgumentParser]) -> ArgumentParser:
        """
        Get a subparser for the command, add_arguments will add all the
        arguments we need.
        """

        return subparsers.add_parser(
            cls.get_name(),
            prog='sysconf ' + cls.get_name(),
            description='Open the target configuration in an editor, wait for '
            'the editor to exit, then prompts whether to apply the '
            'updated configuration to the system.',
            help='Edit the configuration',
            # formatter_class=RawDescriptionHelpFormatter,
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
        new_path = comparative_parser.new_path
        old_path = comparative_parser.old_path
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
        should_override_config_path: bool = False,
    ) -> Self:
        """
        Create an instance of the command from the given context.
        """

        executor = context.get_system_executor()
        file_reader = context.get_file_reader()
        config_reader = ConfigReader(file_reader)

        editor_resolver = EditorResolver(sys.platform, shutil.which)
        editor_launcher = EditorLauncher(executor)

        def preview_command_factory() -> 'PreviewCommand':
            from sysconf.commands.preview_command import PreviewCommand

            preview_command = PreviewCommand.create_from_context(
                context=context,
                old_path=old_path,
                new_path=new_path,
            )

            return preview_command

        def apply_command_factory() -> 'ApplyCommand':
            from sysconf.commands.apply_command import ApplyCommand

            apply_command = ApplyCommand.create_from_context(
                context=context,
                old_path=old_path,
                new_path=new_path,
                should_override_config_path=should_override_config_path,
            )

            return apply_command

        return cls(
            config_reader=config_reader,
            old_path=old_path,
            new_path=new_path,
            editor_resolver=editor_resolver,
            editor_launcher=editor_launcher,
            preview_command_factory=preview_command_factory,
            apply_command_factory=apply_command_factory,
        )

    def __init__(
        self,
        config_reader: ConfigReader,
        old_path: Path,
        new_path: Path,
        editor_resolver: EditorResolver,
        editor_launcher: EditorLauncher,
        preview_command_factory: 'Callable[[], PreviewCommand]',
        apply_command_factory: 'Callable[[], ApplyCommand]',
    ) -> None:
        super().__init__()

        self.config_reader = config_reader
        self.new_path = new_path
        self.old_path = old_path
        self.editor_resolver = editor_resolver
        self.editor_launcher = editor_launcher
        self.preview_command_factory = preview_command_factory
        self.apply_command_factory = apply_command_factory

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, EditCommand):
            return False

        return self.config_reader == value.config_reader \
            and self.new_path == value.new_path \
            and self.old_path == value.old_path \
            and self.editor_resolver == value.editor_resolver \
            and self.editor_launcher == value.editor_launcher \
            # excluded:
        # and self.preview_command_factory == value.preview_command_factory
        # and self.apply_command_factory == value.apply_command_factory

    def run(self) -> Command | None:
        """
        Execute the command.

        Opens the config in the editor, then loads it and validates it, then if
        it differs from the current config, asks the user whether to apply it.

        Raises:
            ValidationError: If the editor exits with an error, or the config
                is invalid and the user chooses not to edit it again.
        """

        old_config = self.config_reader.load_or_default(self.old_path)
        editor_command = self.editor_resolver \
            .get_editor_command(old_config.settings.editor)
        edit_result = self.editor_launcher.edit(
            editor_command,
            self.new_path,
        )

        match edit_result:
            case EditResult.CANCELLED:
                message = 'The editor exited with an error, ' \
                    + 'the edited config was not applied'
                raise ValidationError(message)
            case EditResult.CLOSED:
                pass

        try:
            new_config = self.config_reader.load(self.new_path)
        except ValidationError as error:
            if self.prompt_to_edit_invalid_config(error):
                return self

            raise ValidationError(
                'The invalid config was not applied',
            ) from error

        # offer to apply for any changes to the config, even when no action
        # needs to run
        # e.g. when changing tool settings only
        has_config_changed_from_current = old_config != new_config
        if has_config_changed_from_current:
            choice = self.prompt_to_apply()

            match choice:
                case ApplyChoice.APPLY:
                    return self.apply_command_factory()
                case ApplyChoice.EDIT:
                    return self
                case ApplyChoice.EXIT:
                    print('The edited config was not applied.')
                    return None
        else:
            print('# No changes.')
            return None

    def prompt_to_edit_invalid_config(self, error: ValidationError) -> bool:
        """
        Show why the config is invalid and ask the user whether to edit it.

        Notes:
        - The user gets up to 5 attempts to make a selection before the edit
          is declined

        Returns:
            bool: True if the user chose to edit the config again.
        """

        error_message = str(error)
        print('The config is invalid:')
        print(error_message)
        print()  # Empty line

        for _ in range(5):  # Limit to 5 attempts
            print('Choose an option:')
            print('[e] Edit config')
            print('[a] Abort')

            choice = input('e/a: ').strip().lower()
            match choice:
                case 'e':
                    return True
                case 'a':
                    return False
                case _:
                    print('Invalid choice. Please try again.')

        return False

    def prompt_to_apply(self) -> ApplyChoice:
        """
        Ask the user whether to apply the config, preview its actions, edit it
        again or exit.

        Notes:
        - The user is asked again after each preview
        - The user gets up to 5 invalid selections before the apply is declined

        Returns:
            ApplyChoice: The user's choice, EXIT when the invalid selections
                are exhausted.
        """

        invalid_choices = 0
        while invalid_choices < 5:  # Limit to 5 invalid choices
            print('Apply changes:')
            print('[y] Apply config')
            print('[p] Preview actions')
            print('[e] Edit config')
            print('[n] Exit without applying')

            choice = input('y/p/e/n: ').strip().lower()
            match choice:
                case 'y' | 'yes' | 'apply' | 'a':
                    return ApplyChoice.APPLY
                case 'p' | 'preview':
                    self.preview_actions()
                case 'e' | 'edit':
                    return ApplyChoice.EDIT
                case 'n' | 'no' | 'x' | 'exit':
                    return ApplyChoice.EXIT
                case _:
                    invalid_choices += 1
                    print('Invalid choice. Please try again.')

        return ApplyChoice.EXIT

    def preview_actions(self) -> None:
        """
        Print the actions the apply command would run, without running them.
        """

        print('Planned actions:')
        print()  # Empty line

        preview_command = self.preview_command_factory()
        preview_command.run()
