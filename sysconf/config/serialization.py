# pyright: strict

from pathlib import Path
from typing import Union

import yaml

from sysconf.utils.file import FileReader


YamlSerializable = Union[
    None,
    str,
    int,
    float,
    bool,
    list['YamlSerializable'],
    dict[str, 'YamlSerializable']
]


class YamlDeserializer:
    """
    A deserializer for YAML configuration files.

    Currently only wraps PyYAML, but will hopefully be extended to support features such as $ref
    which are not supported by vanilla yaml.
    """

    def get_data_from_file(self, file_reader: FileReader, path: Path) -> YamlSerializable:
        """
        Read YAML data from a file and return it as a Python object.

        Args:
            file_reader (FileReader): The file reader to use.
            path (Path): The path to the YAML file.

        Returns:
            YamlSerializable: The deserialized YAML data.
        """

        content: str = file_reader.get_file_contents(path)
        return self.get_data(content)

    def get_data(self, content: str) -> YamlSerializable:
        yaml_data = yaml.load(content, Loader=yaml.SafeLoader)
        return yaml_data
