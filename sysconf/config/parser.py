# pyright: strict

from abc import ABC, abstractmethod
from typing import Iterable, Type, cast

from sysconf.config import domain_registry
from sysconf.config.domains import Domain, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.config.system_config import SystemConfig


VERSION_1 = '1'


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
            VERSION_1: SystemConfigParserV1,
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

        assert 'config' in data
        config_items = data['config'] or []

        # validate data
        assert isinstance(config_items, list), \
            'config must be a list of domain mappings'
        for config_item in config_items:
            assert isinstance(config_item, dict), \
                'each config item must be a mapping of domain keys to domain data'
            for key in config_item:
                assert key in self.domains_by_key, \
                    f'Unknown domain key: {key}'

        # parse domain data
        config_entries: Iterable[DomainConfigEntry] = tuple(
            entry
            for task in config_items
            if isinstance(task, dict)
            for domain_key, value in task.items()
            if domain_key in self.domains_by_key
            for entry in self.domains_by_key[domain_key].get_config_entries(
                value,
            )
        )

        return SystemConfig.create_from_config_entries(config_entries)


class SystemConfigRenderer:
    """
    Renders a SystemConfig object into a serializable format (e.g., dicts, lists, scalars).
    """

    def render_config(self, system_config: SystemConfig) -> YamlSerializable:
        """
        Render the given SystemConfig object into a serializable format.

        Args:
            system_config (SystemConfig): The system configuration to render.
        Returns:
            YamlSerializable: The rendered configuration data.
        """

        entries_grouped_by_domain: list[tuple[Domain, list[DomainConfigEntry]]] = []

        for entry in system_config.config_entries.values():
            # get the domain of the last group (if it exists)
            current_domain: Domain | None = entries_grouped_by_domain[-1][0] \
                if entries_grouped_by_domain \
                else None

            # if the entry's domain is different from the current domain,
            # start a new group
            if current_domain != entry.get_domain():
                entries_grouped_by_domain.append((
                    entry.get_domain(),
                    [],
                ))
            
            entries_grouped_by_domain[-1][1].append(entry)

        # render each domain's entries
        config_items: list[dict[str, YamlSerializable]] = [
            {domain.get_key(): domain.render_config_entries(entries)}
            for domain, entries in entries_grouped_by_domain
        ]

        return cast(
            YamlSerializable,
            {
                'version': VERSION_1,
                'config': config_items,
            },
        )
