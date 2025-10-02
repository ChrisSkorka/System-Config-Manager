# pyright: strict

from pathlib import Path
from typing import Union

import yaml


EndNode = Union[None, str, int, float, bool]
YamlSerializable = Union[
    EndNode,
    list['YamlSerializable'],
    dict[str, 'YamlSerializable']
]


class YamlDeserializer:
    """
    A deserializer for YAML configuration files.

    Currently only wraps PyYAML, but will hopefully be extended to support features such as $ref
    which are not supported by vanilla yaml.
    """

    def get_data_from_file(self, path: Path) -> YamlSerializable:

        with open(path, 'r') as f:
            return self.get_data(f.read())

    def get_data(self, content: str) -> YamlSerializable:
        yaml_data = yaml.load(content, Loader=yaml.SafeLoader)
        return yaml_data
