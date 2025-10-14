# pyright: strict


from typing import Callable, Iterable, Self
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainConfigEntry, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.data import get_flattened_dict
from sysconf.utils.diff import Diff


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

    def get_domain_config(self, data: YamlSerializable) -> 'ListConfig':
        return ListConfig.create_from_data(self, data, self.path_depth, self.get_value)

    def get_domain_manager(self, old_config: DomainConfig, new_config: DomainConfig) -> 'ListManager':
        assert isinstance(old_config, ListConfig)
        assert isinstance(new_config, ListConfig)

        return ListManager(
            old_config,
            new_config,
            self.add_action_factory,
            self.remove_action_factory,
        )

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


class ListConfig(DomainConfig):

    def __init__(
        self,
        domain: ListDomain,
        values: tuple[PathValuePair, ...],
    ) -> None:
        super().__init__()

        self.domain = domain
        self.values: tuple[PathValuePair, ...] = values

    @classmethod
    def create_from_data(
        cls,
        domain: ListDomain,
        data: YamlSerializable,
        path_depth: int,
        get_value: Callable[[YamlSerializable], Value],
    ) -> Self:
        if data is None:
            raise NotImplementedError('todo')

        assert isinstance(data, list) or isinstance(data, dict)

        flattened_map = get_flattened_dict(data, path_depth)

        # flatten doct of lists into list of (keys, item) pairs
        values: tuple[tuple[Path, Value], ...] = tuple(
            (keys, get_value(item))
            for keys, items in flattened_map.items()
            if isinstance(items, list)
            for item in items
        )

        return cls(domain, values)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, ListConfig):
            return False
        return self.values == value.values

    def get_config_entries(self) -> Iterable['DomainConfigEntry']:
        return [
            ListConfigEntry(
                domain=self.domain,
                path=keys,
                value=value,
            )
            for keys, value in self.values
        ]


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


class ListManager(DomainManager):

    def __init__(
        self,
        old: ListConfig,
        new: ListConfig,
        add_action_factory: ActionFactory,
        remove_action_factory: ActionFactory,
    ) -> None:
        super().__init__()

        self.old = old
        self.new = new
        self.add_action_factory = add_action_factory
        self.remove_action_factory = remove_action_factory

    def get_actions(self) -> Iterable[DomainAction]:
        diff: Diff[PathValuePair] = Diff[PathValuePair].create_from_iterables(
            self.old.values,
            self.new.values,
        )

        # removals first, in reverse order
        for keys, item in reversed(diff.exclusive_old):
            yield self.remove_action_factory(keys, item)

        # additions next, in normal order
        for keys, item in diff.exclusive_new:
            yield self.add_action_factory(keys, item)
