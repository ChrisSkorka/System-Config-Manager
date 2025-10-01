
from pathlib import Path
from typing import Union

import yaml


EndNode = Union[None, str, int, float, bool]
YamlSerializable = Union[
    EndNode,
    list['YamlSerializable'],
    dict[str, 'YamlSerializable']
]
ConfigDataType = dict[str, YamlSerializable]


class YamlLoader:
    """
    A loader for YAML configuration files.

    Currently only wrapt PyYAML, but will hopefully be extended to support features such as $ref 
    which are not supported by vanilla yaml.
    """

    def get_data_from_file(self, path: Path) -> ConfigDataType:

        with open(path, 'r') as f:
            return self.get_data(f.read())

    def get_data(self, content: str) -> ConfigDataType:
        yaml_data = yaml.load(content, Loader=yaml.SafeLoader)
        return yaml_data
