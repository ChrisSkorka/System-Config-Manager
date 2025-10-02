# pyright: strict

from abc import ABC, abstractmethod
from typing import Type

from sysconf.config import domain_registry
from sysconf.config.domain_registry import domains_by_key
from sysconf.config.domains import DomainConfig
from sysconf.config.serialization import YamlSerializable
from sysconf.config.system_config import SystemConfig


class SystemConfigParser(ABC):
    """
    Abstract base class for system configuration parsers.

    A parser converts the deserialized data (dicts, lists, scalars) into a SystemConfig object.
    """

    @abstractmethod
    def parse_data(self, data: YamlSerializable) -> SystemConfig:
        """
        Parse the given data into a SystemConfig object.

        Also performs schema validation.
        Args:
            data (YamlSerializable): The data to parse.
        Returns:
            SystemConfig: The parsed & validated system configuration.
        """
        pass

    @staticmethod
    def get_parsers_by_version() -> dict[str, Type['SystemConfigParser']]:
        """
        Get a mapping of version strings to parser classes.
        """
        return {
            '1': SystemConfigParserV1,
        }

    @staticmethod
    def get_parser(data: YamlSerializable) -> 'SystemConfigParser':
        """
        Get the appropriate parser for the given data based on its version.

        This validates the 'version' key but does not validate the rest of the data, the returned
        parser is responsible for validating the rest of the data.

        Args:
            data (YamlSerializable): The data to get the parser for.
        Returns:
            SystemConfigParser: The appropriate parser for the given data.
        """

        # validate version key exists
        assert isinstance(data, dict), "Data must be a dictionary"
        assert 'version' in data, "Data must contain a 'version' key"

        version = str(data['version'])
        parsers = SystemConfigParser.get_parsers_by_version()

        # validate version is supported
        assert version in parsers, \
            f"Unsupported version: {version}, supported versions: {list(parsers.keys())}"

        return parsers[version]()


class SystemConfigParserV1(SystemConfigParser):
    """
    System configuration parser for version 1.
    """

    def parse_data(self, data: YamlSerializable) -> SystemConfig:

        assert isinstance(data, dict)

        # version is not part of the config data
        data = {k: v for k, v in data.items() if k != 'version'}

        # validate keys
        for key in data:
            assert key in domain_registry.domains_by_key, \
                f"Unknown domain key: {key}"

        # parse domain data
        domain_map: dict[str, DomainConfig] = {
            key: domains_by_key[key].get_config_from_data(value)
            for key, value
            in data.items()
        }

        return SystemConfig(domain_map)
