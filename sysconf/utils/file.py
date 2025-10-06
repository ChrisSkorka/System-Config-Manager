# pyright: strict

from pathlib import Path


class FileReader:
    """
    A simple file reader
    """

    def get_file_contents(self, path: Path) -> str:
        """
        Read the contents of a file and return it as a string.

        Notes:
        - assumes file is a UTF-8 encoded text file

        Args:
            path (Path): The path to the file to open, read, and close.
        Returns:
            str: The contents of the file.
        """

        with open(file=path, mode='r', encoding='utf-8') as file:
            return file.read()