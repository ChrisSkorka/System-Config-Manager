# pyright: strict

from typing import Iterable

from sysconf.config.domains import DomainAction, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.user_domains import UserDomain
from sysconf.system.executor import SystemExecutor


class _MockDomainAction(DomainAction):

    def __init__(
        self,
        description: str,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> None:
        self._description = description
        self._old_entry = old_entry
        self._new_entry = new_entry

    def get_description(self) -> str:
        return self._description

    def get_old_entry(self) -> DomainConfigEntry | None:
        return self._old_entry

    def get_new_entry(self) -> DomainConfigEntry | None:
        return self._new_entry

    def run(self, executor: SystemExecutor) -> None:
        pass


class MockUserDomain(UserDomain):

    def __init__(self, key: str) -> None:
        self._key = key

    def get_key(self) -> str:
        return self._key

    def get_config_entries(self, data: YamlSerializable) -> Iterable[DomainConfigEntry]:
        return []

    def render_config_entries(self, entries: Iterable[DomainConfigEntry]) -> YamlSerializable:
        return []

    def get_action(
        self,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> '_MockDomainAction':
        old_id = '/'.join(old_entry.get_id()) if old_entry else 'None'
        new_id = '/'.join(new_entry.get_id()) if new_entry else 'None'
        return _MockDomainAction(f'{old_id}→{new_id}', old_entry, new_entry)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MockUserDomain) and self._key == other._key

    def __hash__(self) -> int:
        return hash(self._key)

    def __repr__(self) -> str:
        return f'MockUserDomain({self._key!r})'
