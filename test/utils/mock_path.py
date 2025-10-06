# pyright: strict

from pathlib import Path


class MockPath(Path):
    """A mock Path class to simulate different filesystem behaviors if needed."""

    HOME_DIR = Path.home()

    def __init__(  # pyright: ignore[reportInconsistentConstructor]
        self,
        path: str,
        flags: str = '',
        is_file: bool = False,
        is_dir: bool = False,
        is_symlink: bool = False,
        exists: bool = False,
        expanded_path: str | None = None,
    ) -> None:
        super().__init__(path)

        self._path = path
        self._is_file = is_file or 'f' in flags
        self._is_dir = is_dir or 'd' in flags
        self._is_symlink = is_symlink or 'l' in flags
        self._exists = exists or 'e' in flags
        self._expanded_path = expanded_path or path

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return self._is_file

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return self._is_dir

    def is_symlink(self) -> bool:
        return self._is_symlink

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return self._exists

    def expanduser(self) -> 'MockPath':
        # Return a new MockPath with the pre-defined expanded path
        return MockPath(
            path=self._expanded_path,
            is_file=self._is_file,
            is_dir=self._is_dir,
            is_symlink=self._is_symlink,
            exists=self._exists,
            expanded_path=self._expanded_path,
        )

def fpath(path: str) -> MockPath:
    """Convenience function to create a MockPath for an existing file."""
    return MockPath(path, is_file=True, exists=True)

def dpath(path: str) -> MockPath:
    """Convenience function to create a MockPath for an existing directory."""
    return MockPath(path, is_dir=True, exists=True)