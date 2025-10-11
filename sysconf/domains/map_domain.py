# pyright: strict


from typing import Iterable, Self
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff


Path = tuple[str, ...]  # (keys, ...)


class MapDomain(Domain['MapConfig', 'MapManager']):

    def __init__(
        self,
        key: str,
        add_script: str,
        update_script: str,
        remove_script: str,
    ) -> None:
        super().__init__()

        self._key = key
        self.add_script = add_script
        self.update_script = update_script
        self.remove_script = remove_script

    def get_key(self) -> str:
        return self._key

    def get_domain_config(self, data: YamlSerializable) -> 'MapConfig':
        return MapConfig.create_from_data(data)

    def get_domain_manager(self, old_config: 'MapConfig', new_config: 'MapConfig') -> 'MapManager':
        return MapManager(
            old=old_config,
            new=new_config,
            add_script=self.add_script,
            update_script=self.update_script,
            remove_script=self.remove_script,
        )


class MapConfig(DomainConfig):

    def __init__(self, values: dict[Path, str]) -> None:
        super().__init__()

        self.values: dict[Path, str] = values

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        if data is None:
            return cls({})

        assert isinstance(data, dict)

        values: dict[Path, str] = dict(
            cls.get_key_value_pairs((), data),
        )
        return cls(values)

    @staticmethod
    def get_key_value_pairs(keys: tuple[str, ...], value: YamlSerializable) -> Iterable[tuple[Path, str]]:

        # base case:
        if not isinstance(value, dict):
            yield (keys, str(value))

        # recursive case:
        else:
            for key in value:
                yield from MapConfig.get_key_value_pairs(
                    keys + (key,),
                    value[key],
                )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, MapConfig):
            return False
        return self.values == value.values


class MapAction(DomainAction):

    @staticmethod
    def get_interpolated_script(
        script: str,
        keys: tuple[str, ...],
        value: str,
    ) -> str:
        # create a mapping of variable names to values
        variables: dict[str, str] = {
            f'$key{i+1}': key
            for i, key
            in enumerate(keys)
        }
        if len(keys) > 0:
            variables['$key'] = keys[0]
        variables['$value'] = value

        # perform the interpolation, replacing variable names with values
        interpolated_script = script
        for name, value in variables.items():
            interpolated_script = interpolated_script.replace(name, value)

        return interpolated_script


class MapAddAction(MapAction):

    def __init__(self, keys: tuple[str, ...], value: str, script: str) -> None:
        super().__init__()

        self.keys = keys
        self.value = value
        self.script = script

    def get_description(self) -> str:
        return f'Update {'.'.join(self.keys)} = {self.value}'

    def run(self, executor: SystemExecutor) -> None:
        script = MapAction.get_interpolated_script(
            self.script,
            self.keys,
            self.value,
        )
        executor.shell(script)


class MapUpdateAction(MapAction):

    def __init__(self, keys: tuple[str, ...], value: str, script: str) -> None:
        super().__init__()

        self.keys = keys
        self.value = value
        self.script = script

    def get_description(self) -> str:
        return f'Add {'.'.join(self.keys)} = {self.value}'

    def run(self, executor: SystemExecutor) -> None:
        script = MapAction.get_interpolated_script(
            self.script,
            self.keys,
            self.value,
        )
        executor.shell(script)


class MapRemoveAction(MapAction):

    def __init__(self, keys: tuple[str, ...], item: str, script: str) -> None:
        super().__init__()

        self.keys = keys
        self.item = item
        self.script = script

    def get_description(self) -> str:
        return f'Remove {'.'.join(self.keys)} = {self.item}'

    def run(self, executor: SystemExecutor) -> None:
        script = MapAction.get_interpolated_script(
            self.script,
            self.keys,
            self.item,
        )
        executor.shell(script)


class MapManager(DomainManager):

    def __init__(
        self,
        old: MapConfig,
        new: MapConfig,
        add_script: str,
        update_script: str,
        remove_script: str,
    ) -> None:
        super().__init__()

        self.old = old
        self.new = new
        self.add_script = add_script
        self.update_script = update_script
        self.remove_script = remove_script

    def get_actions(self) -> Iterable[MapAction]:

        diff: Diff[tuple[str, ...]] = Diff[tuple[str, ...]].create_from_iterables(
            self.old.values.keys(),
            self.new.values.keys(),
        )

        # removals first, in reverse order
        for path in reversed(diff.exclusive_old):
            value = self.old.values[path]
            yield MapRemoveAction(path, value, self.remove_script)

        # additions next, in normal order
        for path in diff.new:
            value = self.new.values[path]

            # if path is in both old & new, update value if changed
            if path in self.old.values:
                if self.old.values[path] != value:
                    yield MapUpdateAction(path, value, self.update_script)
            # if path is only in new, add it
            else:
                yield MapAddAction(path, value, self.add_script)
