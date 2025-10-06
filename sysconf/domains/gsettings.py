# pyright: strict

from typing import Iterable, Self

from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.dconf import DConfSetAction
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff

GSettingPath = tuple[str, str]  # (schema, key)


class GSettings(Domain['GSettingsConfig', 'GSettingsManager']):
    """
    Domain for gsettings values, can set/reset values.
    """

    @staticmethod
    def get_key() -> str:
        return 'gsettings'

    @classmethod
    def get_config_from_data(cls, data: YamlSerializable) -> 'GSettingsConfig':
        return GSettingsConfig.create_from_data(data)

    @classmethod
    def get_manager(cls, old_config: 'GSettingsConfig', new_config: 'GSettingsConfig') -> 'GSettingsManager':
        assert isinstance(old_config, GSettingsConfig)
        assert isinstance(new_config, GSettingsConfig)

        return GSettingsManager(old_config, new_config)


class GSettingsConfig(DomainConfig):
    """
    Domain config for gsettings values as a flat map of (schema,key) -> value
    """

    def __init__(self, values: dict[GSettingPath, YamlSerializable]) -> None:
        super().__init__()

        self.values = values

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GSettingsConfig):
            return False
        return self.values == other.values

    def __repr__(self) -> str:
        return f"GSettingsConfig({self.values})"

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        values: dict[GSettingPath, YamlSerializable] = {}

        # default to empty config when no data is provided
        if data is None:
            return cls(values)

        assert isinstance(data, dict)

        for schema, key_values in data.items():
            key_values = key_values or {}
            assert isinstance(key_values, dict)

            for key, value in key_values.items():
                values[(schema, key)] = value

        return cls(values)


class GSettingsAction(DomainAction):
    """
    Base class for all gsettings actions.
    """

    def __init__(self, schema: str, key: str) -> None:
        super().__init__()

        self.schema = schema
        self.key = key


class GSettingsSetAction(GSettingsAction):
    """
    Base class for gsettings set actions (add/update).
    """

    def __init__(
        self,
        schema: str,
        key: str,
        value: YamlSerializable,
    ) -> None:
        super().__init__(schema, key)

        self.value = value

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = DConfSetAction.encode_value(self.value)
        executor.exec('gsettings', 'set', self.schema, self.key, encoded_value)


class GSettingsAddAction(GSettingsSetAction):
    """
    Action to add a new gsettings value.
    """

    def get_description(self) -> str:
        return f'Add gsettings: {self.key} = {self.value}'


class GSettingsUpdateAction(GSettingsSetAction):
    """
    Action to update an existing gsettings value.
    """

    def __init__(
        self,
        schema: str,
        key: str,
        old_value: YamlSerializable,
        new_value: YamlSerializable,
    ) -> None:
        super().__init__(schema, key, new_value)

        self.old_value = old_value
        self.new_value = new_value

    def get_description(self) -> str:
        return f'Update gsettings: {self.key} = {self.old_value} -> {self.new_value}'


class GSettingsRemoveAction(GSettingsAction):
    """
    Action to remove an existing gsettings value (reset to default).

    Note that this "unsets" the value, it does not revert to a value previously set by this tool.
    """

    def get_description(self) -> str:
        return f'Remove gsettings: {self.key}'

    def run(self, executor: SystemExecutor) -> None:
        executor.exec('gsettings', 'reset', self.schema, self.key)


class GSettingsManager(DomainManager):
    """
    Manager to compute the actions required to transform one GSettingsConfig into another.
    """

    def __init__(self, old: GSettingsConfig, new: GSettingsConfig) -> None:
        super().__init__()

        self.old = old
        self.new = new

    def get_actions(self) -> Iterable[GSettingsAction]:
        actions: list[GSettingsAction] = []

        diff = Diff[GSettingPath].create_from_iterables(
            tuple(self.old.values.keys()),
            tuple(self.new.values.keys()),
        )

        # removals
        for (schema, key) in reversed(diff.exclusive_a):
            actions.append(GSettingsRemoveAction(schema, key))

        # adds/updates
        for (schema, key) in diff.b:
            new_val = self.new.values[(schema, key)]

            if (schema, key) not in self.old.values:
                actions.append(GSettingsAddAction(schema, key, new_val))
            else:
                old_val = self.old.values[(schema, key)]
                if old_val != new_val:
                    actions.append(
                        GSettingsUpdateAction(schema, key, old_val, new_val)
                    )

        return actions
