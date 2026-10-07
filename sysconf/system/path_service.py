# pyright: strict

from pathlib import Path, PurePath
from typing import Sequence, Set

from sysconf.utils.validation import validate


class PathService:
    """
    Query & modify the file system at given paths.

    Notes:
    - paths are passed around as PurePath values, all OS interaction goes
      through this service
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, PathService)

    def exists(self, path: PurePath) -> bool:
        """Check whether anything exists at the path."""

        return Path(path).exists()

    def is_file(self, path: PurePath) -> bool:
        """Check whether the path is an existing file."""

        return Path(path).is_file()

    def is_dir(self, path: PurePath) -> bool:
        """Check whether the path is an existing directory."""

        return Path(path).is_dir()

    def expand_user(self, path: PurePath) -> PurePath:
        """Expand a leading `~` to the user's home directory."""

        expanded_path = Path(path).expanduser()

        return PurePath(expanded_path)

    def resolve(self, path: PurePath) -> PurePath:
        """
        Make the path absolute.

        Notes:
        - relative paths are relative to the current working directory
        - symlinks & `..` are resolved
        - `~` is not expanded
        """

        resolved_path = Path(path).resolve()

        return PurePath(resolved_path)

    def make_dirs(self, path: PurePath) -> None:
        """Create the directory and any missing parents, if not existing."""

        Path(path).mkdir(parents=True, exist_ok=True)

    def get_validated_file_path(
        self,
        path: PurePath,
        allowed_suffix: Sequence[str] | Set[str] | str | None = None,
    ) -> PurePath:
        """
        Validates that the provided path exists and is a file.

        Args:
            path (PurePath): The path to validate.
        Returns:
            PurePath: The validated path, with `~` expanded.
        Raises:
            ValidationError: If the path does not exist, is not a file, or
                does not have one of the allowed suffixes.
        """

        path = self.expand_user(path)

        is_existing = self.exists(path)
        validate(is_existing, f'File {path} does not exist')
        is_file = self.is_file(path)
        validate(is_file, f'Path {path} is not a file')

        if allowed_suffix is not None:
            # Normalize allowed_suffix to a sequence
            if isinstance(allowed_suffix, str):
                allowed_suffix = (allowed_suffix,)

            validate(
                path.suffix in allowed_suffix,
                f'File {path} is not a valid file type ({allowed_suffix})',
            )

        return path
