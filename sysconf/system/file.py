# pyright: strict

from pathlib import PurePath

from sysconf.system.path_service import PathService


class FileReader:
    """
    A simple file reader
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, FileReader)

    def get_file_contents(self, path: PurePath) -> str:
        """
        Read the contents of a file and return it as a string.

        Notes:
        - assumes file is a UTF-8 encoded text file

        Args:
            path (PurePath): The path to the file to open, read, and close.
        Returns:
            str: The contents of the file.
        """

        with open(file=path, mode='r', encoding='utf-8') as file:
            return file.read()


class FileWriter:
    """
    A simple file writer
    """

    def __init__(self, path_service: PathService) -> None:
        self.path_service = path_service

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, FileWriter):
            return False

        return self.path_service == value.path_service

    def write_file_contents(self, path: PurePath, contents: str) -> None:
        """
        Write the given contents to a file.

        Notes:
        - assumes file is a UTF-8 encoded text file

        Args:
            path (PurePath): The path to the file to open, write, and close.
            contents (str): The contents to write to the file.
        """

        is_file = self.path_service.is_file(path)
        is_existing = self.path_service.exists(path)
        assert is_file or not is_existing, \
            f'File path is not a file: {path}'

        self.path_service.make_dirs(path.parent)

        with open(file=path, mode='w', encoding='utf-8') as file:
            file.write(contents)
