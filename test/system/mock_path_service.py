# pyright: strict

import posixpath

from collections.abc import Collection
from pathlib import PurePath

from sysconf.system.path_service import PathService


DEFAULT_HOME_DIR = '/home/user'
DEFAULT_WORKING_DIR = '/working'


class MockPathService(PathService):
    """
    Simulate a file system holding the given files & directories.

    Notes:
    - files & dirs are absolute, normalized posix paths
    - relative paths are relative to the working directory
    - parent directories are not implied by files, list them in dirs if needed
    - symlinks are not simulated
    """

    def __init__(
        self,
        files: Collection[str] = (),
        dirs: Collection[str] = (),
        home_dir: str = DEFAULT_HOME_DIR,
        working_dir: str = DEFAULT_WORKING_DIR,
    ) -> None:
        self.files = files
        self.dirs = dirs
        self.home_dir = home_dir
        self.working_dir = working_dir
        self.made_dirs: list[str] = []

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockPathService):
            return False

        return (
            set(self.files) == set(value.files)
            and set(self.dirs) == set(value.dirs)
            and self.home_dir == value.home_dir
            and self.working_dir == value.working_dir
            and self.made_dirs == value.made_dirs
        )

    def _get_absolute_path(self, path: PurePath) -> str:
        working_dir = PurePath(self.working_dir)
        absolute_path = working_dir / path
        posix_path = absolute_path.as_posix()

        return posixpath.normpath(posix_path)

    def exists(self, path: PurePath) -> bool:
        is_file = self.is_file(path)
        is_dir = self.is_dir(path)

        return is_file or is_dir

    def is_file(self, path: PurePath) -> bool:
        absolute_path = self._get_absolute_path(path)

        return absolute_path in self.files

    def is_dir(self, path: PurePath) -> bool:
        absolute_path = self._get_absolute_path(path)

        return (
            absolute_path in self.dirs
            or absolute_path in self.made_dirs
        )

    def expand_user(self, path: PurePath) -> PurePath:
        if not path.parts or path.parts[0] != '~':
            return path

        return PurePath(self.home_dir, *path.parts[1:])

    def resolve(self, path: PurePath) -> PurePath:
        absolute_path = self._get_absolute_path(path)

        return PurePath(absolute_path)

    def make_dirs(self, path: PurePath) -> None:
        absolute_path = self._get_absolute_path(path)

        self.made_dirs.append(absolute_path)
