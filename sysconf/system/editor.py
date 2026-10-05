# pyright: strict

import shlex

from enum import Enum, auto
from pathlib import Path
from typing import Callable

from sysconf.system.executor import CommandException, SystemExecutor
from sysconf.utils.validation import ValidationError


# Editors tried in order when none is configured. Only editors that block
# until the file is closed are listed, so the config is not applied early.
FALLBACK_EDITORS_BY_PLATFORM: dict[str, tuple[str, ...]] = {
    'win32': ('notepad',),
    'darwin': ('nano', 'vim', 'vi'),
}
DEFAULT_FALLBACK_EDITORS: tuple[str, ...] = ('editor', 'nano', 'vim', 'vi')


class EditorResolver:
    """
    Resolve the command line used to open a file in an editor.

    The configured editor is split POSIX shell style on every platform, so
    Windows paths containing spaces must be quoted. When no editor is
    configured, a platform specific list of fallback editors is tried.
    """

    def __init__(
        self,
        platform: str,
        which: Callable[[str], str | None],
    ) -> None:
        """
        Args:
            platform (str): The platform, as given by `sys.platform`.
            which (Callable[[str], str | None]): Find the path of an
                executable, as `shutil.which` does.
        """

        self.platform = platform
        self.which = which

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, EditorResolver):
            return False

        return self.platform == value.platform \
            and self.which == value.which

    def get_editor_command(self, editor: str | None) -> tuple[str, ...]:
        """
        Get the editor command line, without the file to edit.

        Args:
            editor (str | None): The configured editor, None when not set.
        Returns:
            tuple[str, ...]: The resolved executable followed by its arguments.
        Raises:
            ValidationError: If the configured editor is invalid or not found,
                or no editor is configured and no fallback is found.
        """

        if editor is not None:
            return self._get_configured_editor_command(editor)

        fallback_editors = FALLBACK_EDITORS_BY_PLATFORM.get(
            self.platform,
            DEFAULT_FALLBACK_EDITORS,
        )

        for fallback_editor in fallback_editors:
            path = self.which(fallback_editor)
            if path is not None:
                return (path,)

        raise ValidationError(
            f'No editor found (tried {", ".join(fallback_editors)}), '
            + f"set one with 'system-config-manager.editor' in your config",
        )

    def _get_configured_editor_command(self, editor: str) -> tuple[str, ...]:
        try:
            arguments = shlex.split(editor)
        except ValueError as error:
            raise ValidationError(
                f"Invalid 'system-config-manager.editor': {error}",
            ) from error

        executable = arguments[0] if arguments else ''
        path = self.which(executable)

        if path is None:
            raise ValidationError(
                f"Editor '{executable}' from 'system-config-manager.editor' was not found",
            )

        return (path, *arguments[1:])


class EditResult (Enum):
    """The outcome of editing a file in an editor."""

    CLOSED = auto()
    CANCELLED = auto()


class EditorLauncher:
    """
    Open a file in an editor and wait for the editor to exit.
    """

    def __init__(self, executor: SystemExecutor) -> None:
        self.executor = executor

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, EditorLauncher):
            return False

        return self.executor == value.executor

    def edit(self, editor_command: tuple[str, ...], path: Path) -> EditResult:
        """
        Open the file in the editor and wait for the editor to exit.

        Notes:
        - An editor that returns before the file is closed (e.g. `code`
          without `--wait`) cannot be told apart from one the user closed

        Args:
            editor_command (tuple[str, ...]): The editor command line, without
                the file to edit.
            path (Path): The file to edit.
        Returns:
            EditResult: CANCELLED if the editor exited with an error, otherwise
                CLOSED.
        """

        try:
            self.executor.command(*editor_command, str(path))
        except CommandException:
            return EditResult.CANCELLED

        return EditResult.CLOSED
