# pyright: strict


from typing import Any, Callable, Generic, Iterable, Protocol, TypeVar, cast
from sysconf.config.domains import Domain, DomainAction, DomainConfigEntry, NoDomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.data import DataStructure, get_flattened_dict


Path = tuple[str, ...]  # (keys, ...)
Value = TypeVar('Value', bound=YamlSerializable)


class AddActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        new_entry: 'MapConfigEntry[Value]',
    ) -> DomainAction: ...


class UpdateActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        old_entry: 'MapConfigEntry[Value]',
        new_entry: 'MapConfigEntry[Value]',
    ) -> DomainAction: ...


class RemoveActionFactory(Protocol, Generic[Value]):
    @staticmethod
    def __call__(
        old_entry: 'MapConfigEntry[Value]',
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

    def get_config_entries(self, data: YamlSerializable) -> 'Iterable[MapConfigEntry[Value]]':

        if data is None:
            return ()

        assert isinstance(data, dict)

        flattened_map: dict[Path, YamlSerializable] = get_flattened_dict(
            data,
            self.path_depth,
        )

        # convert leave nodes to values
        entries = tuple(
            MapConfigEntry[Value](
                domain=self,
                path=path,
                value=self.get_value(value),
            )
            for path, value in flattened_map.items()
        )

        return entries

    def render_config_entries(
        self,
        entries: Iterable[DomainConfigEntry],
    ) -> YamlSerializable:
        data_builder = DataStructure({})
        
        for entry in entries:
            assert isinstance(entry, MapConfigEntry)
            entry = cast(MapConfigEntry[Value], entry)
            
            data_builder[entry.path] = entry.value

        return data_builder.get_data()

    def get_action(
        self,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> DomainAction:
        assert old_entry is None or isinstance(old_entry, MapConfigEntry)
        assert new_entry is None or isinstance(new_entry, MapConfigEntry)
        assert old_entry is not None or new_entry is not None

        # Typing
        if old_entry is not None:
            assert old_entry.get_domain() == self
            old_entry = cast(MapConfigEntry[Value], old_entry)
        if new_entry is not None:
            assert new_entry.get_domain() == self
            new_entry = cast(MapConfigEntry[Value], new_entry)

        match (old_entry, new_entry):
            case (MapConfigEntry(), MapConfigEntry()):
                if old_entry.value != new_entry.value:
                    return self.update_action_factory(
                        old_entry=old_entry,
                        new_entry=new_entry,
                    )
                else:
                    return NoDomainAction(old_entry, new_entry)
            case (MapConfigEntry(), None):
                return self.remove_action_factory(old_entry)
            case (None, MapConfigEntry()):
                return self.add_action_factory(new_entry)
            case _:
                assert False, \
                    f'unable to generate action from {old_entry} and {new_entry}'


class MapConfigEntry(Generic[Value], DomainConfigEntry):

    def __init__(
        self,
        domain: MapDomain[Value],
        path: tuple[str, ...],
        value: Value,
    ) -> None:
        super().__init__()

        self.domain = domain
        self.path = path
        self.value = value

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, MapConfigEntry):
            return False

        value = cast(MapConfigEntry[Any], value)

        return self.domain == value.domain \
            and self.path == value.path \
            and self.value == value.value

    def __repr__(self) -> str:
        return f'MapConfigEntry({self.domain.get_key}, {self.path}, {self.value})'

    def get_id(self) -> tuple[str, ...]:
        return (self.domain.get_key(), *self.path)

    def get_domain(self) -> MapDomain[Value]:
        return self.domain
