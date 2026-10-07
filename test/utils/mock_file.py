# pyright: strict

from pathlib import Path
from typing import Self
from unittest.mock import MagicMock
from sysconf.system.file import FileReader, FileWriter


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

        self.files = files
        self.get_file_contents = MagicMock(side_effect=get_file_contents)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockFileReader):
            return False

        return self.files == value.files

    def _get_normalized_path(self, path: str | Path) -> str:
        return Path(path).expanduser().resolve().as_posix()

    def __call__(self) -> Self:
        """
        When mocking the FileReader class/type, return self as a mock instance.
        """
        return self


class MockFileWriter (FileWriter):
    """
    Mock a FileWriter instance or class and record everything written to it.

    Mock a FileWriter instance or the FileWriter class/type itself
    """

    def __init__(self) -> None:
        self.written_files: dict[str, str] = {}

        # side effect function
        def write_file_contents(path: Path, contents: str) -> None:
            self.written_files[path.as_posix()] = contents

        self.write_file_contents = MagicMock(side_effect=write_file_contents)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockFileWriter):
            return False

        return self.written_files == value.written_files

    def __call__(self) -> Self:
        """
        When mocking the FileWriter class/type, return self as a mock instance.
        """
        return self
