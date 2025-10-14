# pyright: strict


from typing import Callable, Iterable
from sysconf.config.domains import Domain, DomainAction, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.data import get_flattened_dict


Path = tuple[str, ...]  # (keys, ...)
Value = str
PathValuePair = tuple[Path, Value]
ActionFactory = Callable[[Path, Value], DomainAction]


class ListDomain(Domain):

    def __init__(
        self,
        key: str,
        path_depth: int,
        get_value: Callable[[YamlSerializable], Value],
        add_action_factory: ActionFactory,
        remove_action_factory: ActionFactory,
    ) -> None:
        super().__init__()

        self._key = key
        self.path_depth = path_depth
        self.get_value = get_value
        self.add_action_factory = add_action_factory
        self.remove_action_factory = remove_action_factory

    def get_key(self) -> str:
        return self._key

    def get_config_entries(self, data: YamlSerializable) -> 'Iterable[ListConfigEntry]':

        if data is None:
            return ()

        assert isinstance(data, list) or isinstance(data, dict)

        flattened_map = get_flattened_dict(data, self.path_depth)

        assert all(
            isinstance(v, list) or v is None
            for v in flattened_map.values()
        )

        # flatten dict of lists into list of (keys, lists) pairs
        entries: tuple[ListConfigEntry, ...] = tuple(
            # (keys, get_value(item))
            ListConfigEntry(
                domain=self,
                path=keys,
                value=str(item),
            )
            for keys, items in flattened_map.items()
            if isinstance(items, list)
            for item in items
        )

        return entries

    def get_action(
        self,
        old_entry: 'DomainConfigEntry | None',
        new_entry: 'DomainConfigEntry | None',
    ) -> DomainAction | None:
        assert old_entry is None or isinstance(old_entry, ListConfigEntry)
        assert new_entry is None or isinstance(new_entry, ListConfigEntry)
        assert old_entry is not None or new_entry is not None

        if old_entry and new_entry:
            return None  # no update action for list entries
        if old_entry and not new_entry:
            return self.remove_action_factory(old_entry.path, old_entry.value)
        if not old_entry and new_entry:
            return self.add_action_factory(new_entry.path, new_entry.value)


class ListConfigEntry(DomainConfigEntry):

    def __init__(
        self,
        domain: ListDomain,
        path: tuple[str, ...],
        value: str,
    ) -> None:
        super().__init__()

        self.domain = domain
        self.path = path
        self.value = value

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, ListConfigEntry):
            return False

        return self.domain == value.domain \
            and self.path == value.path \
            and self.value == value.value

    def __repr__(self) -> str:
        return f'ListConfigEntry({self.domain.get_key()}, {self.path}, {self.value})'

    def get_id(self) -> tuple[str, ...]:
        return (self.domain.get_key(), *self.path, self.value)

    def get_domain(self) -> ListDomain:
        return self.domain
