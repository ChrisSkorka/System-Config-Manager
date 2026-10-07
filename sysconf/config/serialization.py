# pyright: strict

import yaml

from pathlib import PurePath
from typing import Union

from sysconf.system.file import FileReader
from sysconf.system.path_service import PathService
from sysconf.utils.validation import ValidationError


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

    def get_data_from_file(
        self,
        file_reader: FileReader,
        path_service: PathService,
        path: PurePath,
    ) -> YamlSerializable:
        """
        Read YAML data from a file and return it as a YamlSerializable object.

        Notes:
        - Performs static interpolations

        Args:
            file_reader (FileReader): The file reader to use.
            path_service (PathService): Resolves the file's directory.
            path (PurePath): The path to the YAML file.

        Returns:
            YamlSerializable: The deserialized YAML data.
        """

        content: str = file_reader.get_file_contents(path)
        data = self.get_deserialized_data(content)

        expanded_directory = path_service.expand_user(path.parent)
        resolved_directory = path_service.resolve(expanded_directory)
        directory_path = str(resolved_directory)

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
        """
        Deserialize YAML content.

        Raises:
            ValidationError: If the content is not valid YAML.
        """

        try:
            yaml_data = yaml.load(content, Loader=yaml.SafeLoader)
        except yaml.YAMLError as error:
            raise ValidationError(f'Invalid YAML: {error}') from error

        return yaml_data


class YamlSerializer:
    """
    A serializer for YAML configuration files.
    """

    def __eq__(self, value: object) -> bool:
        return isinstance(value, YamlSerializer)

    def get_serialized_data(self, data: YamlSerializable) -> str:
        """
        Serialize the given data into a YAML string.
        """

        yaml_string = yaml.dump(
            data,
            Dumper=yaml.SafeDumper,
            sort_keys=False,
        )
        return yaml_string
