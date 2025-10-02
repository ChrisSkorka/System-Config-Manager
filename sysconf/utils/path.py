# pyright: strict

from pathlib import Path
from typing import Sequence, Set


def get_validated_file_path(
    path: Path,
    allowed_suffix: Sequence[str] | Set[str] | str,
) -> Path:
    """
    Validates that the provided path exists and is a file.

    Args:
        path (Path): The path to validate.
    Returns:
        Path: The validated path.

    """

    if isinstance(allowed_suffix, str):
        allowed_suffix = (allowed_suffix,)

    path = path.expanduser()

    assert path.exists(), f'File {path} does not exist'
    assert path.is_file(), f'Path {path} is not a file'
    assert path.suffix in allowed_suffix, \
        f'File {path} is not a valid file type ({allowed_suffix})'

    return path
