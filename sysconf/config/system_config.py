
from pathlib import Path
from typing import Self

from sysconf.config.domain_registry import domains
from sysconf.config.domains import DomainConfig
from sysconf.config.loader import ConfigDataType, YamlLoader


class SystemConfig:

    def __init__(self, data: dict[str, DomainConfig]):
        self.data: dict[str, DomainConfig] = data

    @classmethod
    def create_from_file(cls, path: Path) -> Self:

        loader = YamlLoader()
        yaml_data = loader.get_data_from_file(path)
        return cls.create_from_data(yaml_data)

    @classmethod
    def create_from_data(cls, yaml_data: ConfigDataType) -> Self:

        domain_map: dict[str, DomainConfig] = {}
        for domain in domains:
            for path in domain.get_paths():
                domain_data = yaml_data.get(path, None)
                if domain_data is not None:
                    domain_map[path] = domain.get_config_from_data(domain_data)
        return cls(domain_map)

