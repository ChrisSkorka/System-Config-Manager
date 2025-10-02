from typing import Iterable
from sysconf.config import domain_registry
from sysconf.config.domains import DomainAction, DomainConfig
from sysconf.utils.diff import Diff


class SystemConfig:
    """
    Represents the entire system configuration by aggregating multiple domain configurations.
    """

    def __init__(self, data: dict[str, DomainConfig]):
        self.data: dict[str, DomainConfig] = data

    def __repr__(self) -> str:
        return f"SystemConfig({self.data})"


class SystemManager:
    """
    Manages the application of system configurations across multiple domains.
    """

    def __init__(self, old_config: SystemConfig, new_config: SystemConfig):
        self.old_config = old_config
        self.new_config = new_config

    def get_actions(self) -> Iterable[DomainAction]:
        """
        Plan the actions required to transition from the old configuration to the new configuration.
        Returns:
            A list of actions to be performed.
        """
        actions = []

        domain_diff = Diff.create_from_iterables(
            self.old_config.data.keys(),
            self.new_config.data.keys(),
        )

        # remove domains
        for key in domain_diff.exclusive_a:

            old_data = self.old_config.data[key]
            new_data = domain_registry.domains_by_key[key].get_config_from_data(
                None)

            manager = domain_registry.domains_by_key[key].get_manager(
                old_data,
                new_data,
            )
            actions.extend(manager.get_actions())

        # add & update domains
        # add & update are combined so we can process them in the order they're
        # listed in the new config
        for key in domain_diff.b:

            old_data = self.old_config.data[key] \
                if key in self.old_config.data \
                else domain_registry.domains_by_key[key].get_config_from_data(None)
            new_data = self.new_config.data[key]

            manager = domain_registry.domains_by_key[key].get_manager(
                old_data,
                new_data,
            )
            actions.extend(manager.get_actions())

        return actions
