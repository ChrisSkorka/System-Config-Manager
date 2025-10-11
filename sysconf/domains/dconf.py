# pyright: strict

from typing import Iterable, Self

from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff


class DConf(Domain['DConfConfig', 'DConfManager']):
    """
    Domain for dconf values, can set/reset values.
    """

    def get_key(self) -> str:
        return 'dconf'

    def get_domain_config(self, data: YamlSerializable) -> 'DConfConfig':
        return DConfConfig.create_from_data(data)

    def get_domain_manager(self, old_config: 'DConfConfig', new_config: 'DConfConfig') -> 'DConfManager':
        assert isinstance(old_config, DConfConfig)
        assert isinstance(new_config, DConfConfig)

        return DConfManager(old_config, new_config)


class DConfConfig(DomainConfig):
    """
    Domain config for dconf values as a flat map of (schema,key) -> value
    """

    def __init__(self, values: dict[str, YamlSerializable]) -> None:
        super().__init__()

        self.values = values

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DConfConfig):
            return False
        return self.values == other.values

    def __repr__(self) -> str:
        return f"DConfConfig({self.values})"

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        # default to empty config when no data is provided
        if data is None:
            return cls({})

        assert isinstance(data, dict)

        return cls(values=data)


class DConfAction(DomainAction):
    """
    Base class for all dconf actions.
    """

    def __init__(self, path: str) -> None:
        super().__init__()

        self.path = path


class DConfSetAction(DConfAction):
    """
    Base class for dconf set actions (add/update).
    """

    def __init__(
        self,
        path: str,
        value: YamlSerializable,
    ) -> None:
        super().__init__(path)

        self.value = value

    @classmethod
    def encode_value(cls, value: YamlSerializable) -> str:
        match value:
            case n if n is None:
                return f'<@mb nothing>'  # todo: confirm
            case b if isinstance(b, bool):
                return 'true' if b else 'false'
            case n if isinstance(n, (int, float)):
                return f'{n}'
            case s if isinstance(s, str):
                return f'"{s}"'
            case l if isinstance(l, list):
                return f"[{', '.join(cls.encode_value(v) for v in l)}]"
            case d if isinstance(d, dict):
                key_value_pairs = (
                    f'"{k}": {cls.encode_value(v)}' for k, v in d.items())
                return f"{{ {', '.join(key_value_pairs)} }}"
            case _:
                assert False, f'Unsupported value type {type(value)}'

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = self.encode_value(self.value)
        executor.exec('dconf', 'write', self.path, encoded_value)


class DConfAddAction(DConfSetAction):
    """
    Action to add a new dconf value.
    """

    def get_description(self) -> str:
        return f'Add dconf: {self.path} = {self.value}'


class DConfUpdateAction(DConfSetAction):
    """
    Action to update an existing dconf value.
    """

    def __init__(
        self,
        path: str,
        old_value: YamlSerializable,
        new_value: YamlSerializable,
    ) -> None:
        super().__init__(path, new_value)

        self.old_value = old_value

    def get_description(self) -> str:
        return f'Update dconf: {self.path} = {self.old_value} -> {self.value}'


class DConfRemoveAction(DConfAction):
    """
    Action to remove an existing dconf value (reset to default).

    Note that this "unsets" the value, it does not revert to a value previously set by this tool.
    """

    def get_description(self) -> str:
        return f'Remove dconf: {self.path}'

    def run(self, executor: SystemExecutor) -> None:
        executor.exec('dconf', 'reset', self.path)


class DConfManager(DomainManager):
    """
    Manager to compute the actions required to transform one GSettingsConfig into another.
    """

    def __init__(self, old: DConfConfig, new: DConfConfig) -> None:
        super().__init__()

        self.old = old
        self.new = new

    def get_actions(self) -> Iterable[DConfAction]:
        actions: list[DConfAction] = []

        diff = Diff[str].create_from_iterables(
            tuple(self.old.values.keys()),
            tuple(self.new.values.keys()),
        )

        # removals
        for path in reversed(diff.exclusive_old):
            actions.append(DConfRemoveAction(path))

        # adds/updates
        for path in diff.new:
            new_val = self.new.values[path]

            if path not in self.old.values:
                actions.append(DConfAddAction(path, new_val))
            else:
                old_val = self.old.values[path]
                if old_val != new_val:
                    actions.append(
                        DConfUpdateAction(path, old_val, new_val)
                    )

        return actions
