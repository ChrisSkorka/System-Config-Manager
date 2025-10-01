
from abc import ABC, abstractmethod
from typing import Iterable, Generic, Self, TypeVar

from sysconf.config.loader import YamlSerializable


D = TypeVar('D', bound='Domain')


class Domain(ABC):
    """
    A domain represents a specific area of system configuration, such as
    apt packages, config files, or user settings.

    Each domain needs to implement:
    - A `Domain` (this class) which serves as generic ID for the following types
    - A `DomainConfig` which represents the configuration data for this domain
    - A `Manager` which can compare two `DomainConfig`s and produce a list of `Action`s
    - One or more `Action` which can be executed to apply a change to the system
    """

    @staticmethod
    @abstractmethod
    def get_paths() -> Iterable[str]:
        """
        Get the data paths relevant to this domain.
        """
        pass

    @classmethod
    @abstractmethod
    def get_config_from_data(cls, data: YamlSerializable) -> 'DomainConfig[Self]':
        """
        Create a new instance of the domain configuration from the given data.

        Args:
            data (YamlSerializable): The data to create the domain configuration from.
        Returns:
            DomainConfig: A new instance of the domain configuration.
        """
        pass

    @classmethod
    @abstractmethod
    def get_manager(cls, old_config: 'DomainConfig[Self]', new_config: 'DomainConfig[Self]') -> 'DomainManager[Self]':
        """
        Get a manager for this domain.

        Args:
            old_config (DomainConfig): The old configuration for this domain.
            new_config (DomainConfig): The new configuration for this domain.
        Returns:
            DomainManager: A manager for this domain.
        """
        pass


class DomainConfig(ABC, Generic[D]):
    """
    Base class for all domain configurations.

    This parses the configuration data for a specific domain and stores it in a structured way.
    """

    @classmethod
    @abstractmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        """
        Create a new instance of the domain configuration from the given data.

        Args:
            data (YamlSerializable): The data to create the domain configuration from.
        Returns:
            Self: A new instance of the domain configuration.
        """
        pass


class DomainAction(ABC, Generic[D]):
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
        pass

    @abstractmethod
    # todo: add a param to inject some system/shell executor
    def run(self) -> None:
        """
        Execute the action.

        This will perform actual action including executing system commands.
        """
        pass


class DomainManager(Generic[D], ABC):
    """
    Base class for all domain managers.

    A domain manager is responsible for comparing two domain configurations and producing a list of
    actions to be performed to transform the system from the old configuration to the new
    configuration.
    """

    @abstractmethod
    def get_actions(self, old: DomainConfig[D], new: DomainConfig[D]) -> Iterable[DomainAction[D]]:
        """
        Get a list of actions to be performed to transform the system from the old configuration to
        the new configuration.
        """
        pass
        # todo: make args instance vars?
