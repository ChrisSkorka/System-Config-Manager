# pyright: strict

from abc import ABC, abstractmethod
from typing import Iterable, Type

from sysconf.config import domain_registry
from sysconf.config.domains import Domain, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.config.system_config import SystemConfig


class SystemConfigParser(ABC):
    """
    Abstract base class for system configuration parsers.

    A parser converts the deserialized data (dicts, lists, scalars) into a SystemConfig object.
    """

    def __init__(self, domains_by_key: dict[str, Domain]):
        super().__init__()

        self.domains_by_key = domains_by_key

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
        pass  # pragma: no cover

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

        return parsers[version](domain_registry.domains_by_key)


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
            assert key in self.domains_by_key, \
                f"Unknown domain key: {key}"

        # parse domain data
        config_entries: Iterable[DomainConfigEntry] = (
            entry
            for domain_key, value in data.items()
            for entry in self.domains_by_key[domain_key].get_domain_config(value).get_config_entries()
        )

        return SystemConfig.create_from_config_entries(config_entries)
