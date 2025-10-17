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

    Notes:
    - Performs static interpolations ($pwd)
    """

    def get_data_from_file(self, file_reader: FileReader, path: Path) -> YamlSerializable:
        """
        Read YAML data from a file and return it as a YamlSerializable object.

        Notes:
        - Performs static interpolations

        Args:
            file_reader (FileReader): The file reader to use.
            path (Path): The path to the YAML file.

        Returns:
            YamlSerializable: The deserialized YAML data.
        """

        content: str = file_reader.get_file_contents(path)
        data = self.get_deserialized_data(content)

        directory_path = str(path.parent.expanduser().resolve())

        interpolated_data = self.get_interpolated_data(
            data,
            {
                '$pwd': directory_path,
            },
        )

        return interpolated_data

    def get_interpolated_data(
        self,
        data: YamlSerializable,
        replacements: dict[str, str],
    ) -> YamlSerializable:
        """
        Returns a new data structure with the replacements applied to all 
        string values by recursively finding string leave nodes and perform 
        replacements.

        Notes:
        - New collections are created (originals objects are not modified).
        - Only leave string nodes are modified.
        - Dictionary/map keys are not modified.
        """

        # base case: str
        if isinstance(data, str):
            for search, replace in replacements.items():
                data = data.replace(search, replace)

        # base case: other scalar values
        # no action required

        # recursive case: list
        if isinstance(data, list):
            data = [
                self.get_interpolated_data(item, replacements)
                for item in data
            ]

        # recursive case: dict
        if isinstance(data, dict):
            data = {
                key: self.get_interpolated_data(item, replacements)
                for key, item in data.items()
            }

        return data

    def get_deserialized_data(self, content: str) -> YamlSerializable:
        yaml_data = yaml.load(content, Loader=yaml.SafeLoader)
        return yaml_data
