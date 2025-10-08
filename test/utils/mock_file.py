# pyright: strict

from pathlib import Path
from typing import Self
from unittest.mock import MagicMock
from sysconf.utils.file import FileReader


class MockFileReader (FileReader):
    """
    Mock a FileReader instance or class to return predefined file contents.

    Mock a FileReader instance or the FileReader class/type itself
    """

    def __init__(self, files: dict[str, str]) -> None:
        # normalize paths
        files = {
            self._get_normalized_path(path): content
            for path, content 
            in files.items()
        }

        # side effect function
        def get_file_contents(path: Path) -> str:
            return files[self._get_normalized_path(path)]

        self.get_file_contents = MagicMock(side_effect=get_file_contents)

    def _get_normalized_path(self, path: str | Path) -> str:
        return Path(path).expanduser().resolve().as_posix()

    def __call__(self) -> Self:
        """
        When mocking the FileReader class/type, return self as a mock instance.
        """
        return self