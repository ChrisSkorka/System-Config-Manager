# pyright: strict

from pathlib import Path
from typing import Sequence, Set

from sysconf.utils.validation import validate


def get_validated_file_path(
    path: Path,
    allowed_suffix: Sequence[str] | Set[str] | str | None = None,
) -> Path:
    """
    Validates that the provided path exists and is a file.

    Args:
        path (Path): The path to validate.
    Returns:
        Path: The validated path.
    Raises:
        ValidationError: If the path does not exist, is not a file, or does
            not have one of the allowed suffixes.
    """

    path = path.expanduser()

    validate(path.exists(), f'File {path} does not exist')
    validate(path.is_file(), f'Path {path} is not a file')

    if allowed_suffix is not None:
        # Normalize allowed_suffix to a sequence
        if isinstance(allowed_suffix, str):
            allowed_suffix = (allowed_suffix,)

        validate(
            path.suffix in allowed_suffix,
            f'File {path} is not a valid file type ({allowed_suffix})',
        )

    return path
