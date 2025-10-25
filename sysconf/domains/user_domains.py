# pyright: strict

from typing import Iterable, Self

from sysconf.config.domains import Domain, DomainAction, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.list_domain import ListConfigEntry, ListDomain
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from sysconf.domains.shell_domains import create_list_shell_domain, create_map_shell_domain


class UserDomain(Domain):
    """
    A domain that represents user-defined configuration.
    """


class UserListDomain(UserDomain):
    """
    A user-defined list domain.

    Wraps a shell ListDomain but keeps the user-defined specs.
    """

    @classmethod
    def create_from_specs(
        cls,
        key: str,
        path_depth: int,
        add_script: str,
        remove_script: str,
    ) -> Self:
        return cls(
            key,
            path_depth,
            add_script,
            remove_script,
            create_list_shell_domain(
                key,
                path_depth,
                add_script,
                remove_script,
            ),
        )

    def __init__(
        self,
        key: str,
        path_depth: int,
        add_script: str,
        remove_script: str,
        list_domain: ListDomain,
    ) -> None:
        super().__init__()

        self.key = key
        self.path_depth = path_depth
        self.add_script = add_script
        self.remove_script = remove_script
        self.list_domain = list_domain

    def get_key(self) -> str:
        return self.list_domain.get_key()

    def get_config_entries(self, data: YamlSerializable) -> Iterable[ListConfigEntry]:
        return self.list_domain.get_config_entries(data)

    def render_config_entries(
        self,
        entries: Iterable[DomainConfigEntry],
    ) -> YamlSerializable:
        return self.list_domain.render_config_entries(entries)

    def get_action(
        self,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> DomainAction:
        return self.list_domain.get_action(old_entry, new_entry)

    def render(self) -> YamlSerializable:
        return {
            'depth': self.path_depth,
            'add': self.add_script,
            'remove': self.remove_script,
        }


class UserMapDomain(UserDomain):
    """
    A user-defined map domain.

    Wraps a shell MapDomain but keeps the user-defined specs.
    """

    @classmethod
    def create_from_specs(
        cls,
        key: str,
        path_depth: int,
        add_script: str,
        update_script: str,
        remove_script: str,
    ) -> Self:
        return cls(
            key,
            path_depth,
            add_script,
            update_script,
            remove_script,
            create_map_shell_domain(
                key,
                path_depth,
                add_script,
                update_script,
                remove_script,
            ),
        )

    def __init__(
        self,
        key: str,
        path_depth: int,
        add_script: str,
        update_script: str,
        remove_script: str,
        map_domain: MapDomain[str],
    ) -> None:
        super().__init__()

        self.key = key
        self.path_depth = path_depth
        self.add_script = add_script
        self.update_script = update_script
        self.remove_script = remove_script
        self.map_domain = map_domain

    def get_key(self) -> str:
        return self.map_domain.get_key()

    def get_config_entries(self, data: YamlSerializable) -> Iterable[MapConfigEntry[str]]:
        return self.map_domain.get_config_entries(data)

    def render_config_entries(
        self,
        entries: Iterable[DomainConfigEntry],
    ) -> YamlSerializable:
        return self.map_domain.render_config_entries(entries)

    def get_action(
        self,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> DomainAction:
        return self.map_domain.get_action(old_entry, new_entry)

    def render(self) -> YamlSerializable:
        return {
            'depth': self.path_depth,
            'add': self.add_script,
            'remove': self.remove_script,
        }
