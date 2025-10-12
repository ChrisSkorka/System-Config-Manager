# pyright: strict


from typing import Any, Callable, Generic, Iterable, Protocol, Self, TypeVar, cast
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.data import get_flattened_dict
from sysconf.utils.diff import Diff


Path = tuple[str, ...]  # (keys, ...)
Value = TypeVar('Value', contravariant=True)


class AddActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        path: Path,
        new_value: Value,
    ) -> DomainAction: ...


class UpdateActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        path: Path,
        old_value: Value,
        new_value: Value,
    ) -> DomainAction: ...


class RemoveActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        path: Path,
        old_value: Value,
    ) -> DomainAction: ...


class MapDomain(Generic[Value], Domain):

    def __init__(
        self,
        key: str,
        path_depth: int,
        get_value: Callable[[YamlSerializable], Value],
        add_action_factory: AddActionFactory[Value],
        update_action_factory: UpdateActionFactory[Value],
        remove_action_factory: RemoveActionFactory[Value],
    ) -> None:
        super().__init__()

        self._key = key
        self.path_depth = path_depth
        self.get_value = get_value
        self.add_action_factory = add_action_factory
        self.update_action_factory = update_action_factory
        self.remove_action_factory = remove_action_factory

    def get_key(self) -> str:
        return self._key

    def get_domain_config(self, data: YamlSerializable) -> 'MapConfig[Value]':
        return MapConfig[Value].create_from_data(data, self.path_depth, self.get_value)

    def get_domain_manager(self, old_config: DomainConfig, new_config: DomainConfig) -> 'MapManager[Value]':
        assert isinstance(old_config, MapConfig)
        assert isinstance(new_config, MapConfig)

        old_config = cast(MapConfig[Value], old_config)
        new_config = cast(MapConfig[Value], new_config)

        return MapManager(
            old=old_config,
            new=new_config,
            add_action_factory=self.add_action_factory,
            update_action_factory=self.update_action_factory,
            remove_action_factory=self.remove_action_factory,
        )


class MapConfig(Generic[Value], DomainConfig):

    def __init__(self, values: dict[Path, Value]) -> None:
        super().__init__()

        self.values: dict[Path, Value] = values

    @classmethod
    def create_from_data(
        cls,
        data: YamlSerializable,
        path_depth: int,
        get_value: Callable[[YamlSerializable], Value],
    ) -> Self:
        if data is None:
            return cls({})

        assert isinstance(data, dict)

        flattened_map: dict[Path, YamlSerializable] = get_flattened_dict(
            data,
            path_depth,
        )

        # convert leave nodes to values
        values = {
            keys: get_value(value)
            for keys, value in flattened_map.items()
        }

        return cls(values)

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, MapConfig):
            return False

        other = cast(MapConfig[Any], other)

        return self.values == other.values


class MapManager(Generic[Value], DomainManager):

    def __init__(
        self,
        old: MapConfig[Value],
        new: MapConfig[Value],
        add_action_factory: AddActionFactory[Value],
        update_action_factory: UpdateActionFactory[Value],
        remove_action_factory: RemoveActionFactory[Value],
    ) -> None:
        super().__init__()

        self.old = old
        self.new = new
        self.add_action_factory = add_action_factory
        self.update_action_factory = update_action_factory
        self.remove_action_factory = remove_action_factory

    def get_actions(self) -> Iterable[DomainAction]:

        diff: Diff[tuple[str, ...]] = Diff[tuple[str, ...]].create_from_iterables(
            self.old.values.keys(),
            self.new.values.keys(),
        )

        # removals first, in reverse order
        for path in reversed(diff.exclusive_old):
            old_value = self.old.values[path]
            yield self.remove_action_factory(path, old_value)

        # additions next, in normal order
        for path in diff.new:
            new_value = self.new.values[path]

            # if path is in both old & new, update value if changed
            if path in self.old.values:
                old_value = self.old.values[path]
                if old_value != new_value:
                    yield self.update_action_factory(path, old_value, new_value)
            # if path is only in new, add it
            else:
                yield self.add_action_factory(path, new_value)
