# pyright: strict


from typing import Iterable, Self
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff


PathValuePair = tuple[tuple[str, ...], str]  # ((keys, ...), value)


class ListDomain(Domain['ListConfig', 'ListManager']):

    def __init__(
        self,
        key: str,
        add_script: str,
        remove_script: str,
    ) -> None:
        super().__init__()

        self._key = key
        self.add_script = add_script
        self.remove_script = remove_script

    def get_key(self) -> str:
        return self._key

    def get_domain_config(self, data: YamlSerializable) -> 'ListConfig':
        return ListConfig.create_from_data(data)

    def get_domain_manager(self, old_config: 'ListConfig', new_config: 'ListConfig') -> 'ListManager':
        return ListManager(
            old_config,
            new_config,
            self.add_script,
            self.remove_script,
        )


class ListConfig(DomainConfig):

    def __init__(self, values: tuple[PathValuePair, ...]) -> None:
        super().__init__()

        self.values: tuple[PathValuePair, ...] = values

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        if data is None:
            return cls(())

        assert isinstance(data, list) or isinstance(data, dict)

        values: tuple[PathValuePair, ...] = tuple(
            cls.get_key_value_pairs((), data),
        )
        return cls(values)

    @staticmethod
    def get_key_value_pairs(keys: tuple[str, ...], value: YamlSerializable) -> Iterable[PathValuePair]:

        # base case:
        if isinstance(value, list):

            # todo: validate that all items are scalar

            yield from (
                (keys, str(item))
                for item in value
            )

        # recursive case:
        elif isinstance(value, dict):
            for key in value:
                yield from ListConfig.get_key_value_pairs(
                    keys + (key,),
                    value[key],
                )

        else:
            raise ValueError(
                f'Invalid value type for list config: {type(value)} ({value}). '
                + 'Scalar values can only occur immediately inside a list'
            )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, ListConfig):
            return False
        return self.values == value.values


class ListAction(DomainAction):

    @staticmethod
    def get_interpolated_script(
        script: str,
        keys: tuple[str, ...],
        item: str,
    ) -> str:
        # create a mapping of variable names to values
        variables: dict[str, str] = {
            f'$key{i+1}': key
            for i, key
            in enumerate(keys)
        }
        if len(keys) > 0:
            variables['$key'] = keys[0]
        variables['$item'] = item

        # perform the interpolation, replacing variable names with values
        interpolated_script = script
        for name, value in variables.items():
            interpolated_script = interpolated_script.replace(name, value)

        return interpolated_script


class ListAddAction(ListAction):

    def __init__(self, keys: tuple[str, ...], item: str, script: str) -> None:
        super().__init__()

        self.keys = keys
        self.item = item
        self.script = script

    def get_description(self) -> str:
        return f'Add {'.'.join(self.keys)} = {self.item}'

    def run(self, executor: SystemExecutor) -> None:
        script = ListAction.get_interpolated_script(
            self.script,
            self.keys,
            self.item,
        )
        executor.shell(script)


class ListRemoveAction(ListAction):

    def __init__(self, keys: tuple[str, ...], item: str, script: str) -> None:
        super().__init__()

        self.keys = keys
        self.item = item
        self.script = script

    def get_description(self) -> str:
        return f'Remove {'.'.join(self.keys)} = {self.item}'

    def run(self, executor: SystemExecutor) -> None:
        script = ListAction.get_interpolated_script(
            self.script,
            self.keys,
            self.item,
        )
        executor.shell(script)


class ListManager(DomainManager):

    def __init__(
        self,
        old: ListConfig,
        new: ListConfig,
        add_script: str,
        remove_script: str,
    ) -> None:
        super().__init__()

        self.old = old
        self.new = new
        self.add_script = add_script
        self.remove_script = remove_script

    def get_actions(self) -> Iterable[ListAction]:
        diff: Diff[PathValuePair] = Diff[PathValuePair].create_from_iterables(
            self.old.values,
            self.new.values,
        )

        # removals first, in reverse order
        for keys, item in reversed(diff.exclusive_old):
            yield ListRemoveAction(keys, item, self.remove_script)

        # additions next, in normal order
        for keys, item in diff.exclusive_new:
            yield ListAddAction(keys, item, self.add_script)
