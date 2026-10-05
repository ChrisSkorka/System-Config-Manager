# pyright: strict

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSettings:
    """
    Settings for this tool itself, as opposed to the system being configured.

    These produce no actions when applied, but are carried along with the
    config so that they travel with it and are recorded in the current
    configuration.

    Attributes:
        editor (str | None): The command line used to open the config in an
            editor, split POSIX shell style. None when not configured.
    """

    editor: str | None = None
