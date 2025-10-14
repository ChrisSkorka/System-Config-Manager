# pyright: strict

from abc import ABC, abstractmethod
from typing import Iterable

from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor


class Domain(ABC):
    """
    A domain represents a specific area of system configuration, such as
    apt packages, config files, or user settings.

    Each domain needs to implement:
    - A `Domain` (this class) which serves as generic ID for the following types
    - A `DomainConfig` which represents the configuration data for this domain
    - A `Manager` which can compare two `DomainConfig`s and produce a list of 
      `Action`s
    - One or more `Action`s which can be executed to apply a change to the
      system
    """

    @abstractmethod
    def get_key(self) -> str:
        """
        Get the domain key that identifies this domain.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_config_entries(self, data: YamlSerializable) -> Iterable['DomainConfigEntry']:
        """
        Get all configuration entries in this domain.

        Returns:
            An iterable of all configuration entries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_action(
        self,
        old_entry: 'DomainConfigEntry | None',
        new_entry: 'DomainConfigEntry | None',
    ) -> 'DomainAction | None':
        """
        Get an action to transform the old entry into the new entry.

        Args:
            old_entry: The old configuration entry.
            new_entry: The new configuration entry.
        Returns:
            An action to transform the old entry into the new entry.
        """
        pass  # pragma: no cover


ConfigEntryId = tuple[str, ...]


class DomainConfigEntry(ABC):

    @abstractmethod
    def get_id(self) -> ConfigEntryId:
        """
        Get a unique identifier for this entry.

        This is used to match this entry against a counterpart in another system
        configuration.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_domain(self) -> Domain:
        """
        Get the domain this entry belongs to.
        """
        pass  # pragma: no cover


class DomainAction(ABC):
    """
    Base class for all actions that can be performed on a domain.
    """

    def __str__(self) -> str:
        return self.get_description()

    @abstractmethod
    def get_description(self) -> str:
        """
        Get a human-readable description of the action.

        This should not include the actual commands to be executed.
        """
        pass  # pragma: no cover

    @abstractmethod
    def run(self, executor: SystemExecutor) -> None:
        """
        Execute the action.

        This will perform actual action including executing system commands.
        """
        pass  # pragma: no cover
