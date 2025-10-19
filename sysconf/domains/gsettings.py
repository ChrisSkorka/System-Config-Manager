# pyright: strict

from typing import Self
from sysconf.config.domains import DomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.dconf import MapDomain, encode_value
from sysconf.domains.map_domain import MapConfigEntry
from sysconf.system.executor import SystemExecutor

GSettingPath = tuple[str, str]  # (schema, key)


def create_gsettings_domain() -> MapDomain[YamlSerializable]:
    """
    Create a MapDomain configured to parse, manage, and generate actions for 
    gsettings settings (gnome).
    """

    return MapDomain[YamlSerializable](
        'gsettings',
        path_depth=2,
        get_value=lambda v: v,
        add_action_factory=GSettingsAddAction.create_from_entry,
        update_action_factory=GSettingsUpdateAction.create_from_entries,
        remove_action_factory=GSettingsRemoveAction.create_from_entry,
    )


class GSettingsAddAction(DomainAction):
    """
    Action to add a new gsettings value.
    """

    def __init__(
        self,
        new_entry: MapConfigEntry[YamlSerializable],
        schema: str,
        key: str,
        new_value: str,
    ) -> None:
        super().__init__()

        self.new_entry = new_entry
        self.schema = schema
        self.key = key
        self.new_value = new_value

    @classmethod
    def create_from_entry(
        cls,
        new_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(new_entry.path) == 2, \
            f'Expected path length 2 (schema, key), got {len(new_entry.path)}: {new_entry.path}'
        schema, key = new_entry.path
        encoded_value = encode_value(new_entry.value)

        return cls(new_entry, schema, key, encoded_value)

    def get_description(self) -> str:
        return f'Add gsettings: {self.key} = {self.new_entry.value}'

    def get_old_entry(self) -> None:
        return None

    def get_new_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        executor.command(
            'gsettings',
            'set',
            self.schema,
            self.key,
            self.new_value,
        )


class GSettingsUpdateAction(DomainAction):
    """
    Action to update an existing gsettings value.
    """

    def __init__(
        self,
        old_entry: MapConfigEntry[YamlSerializable],
        new_entry: MapConfigEntry[YamlSerializable],
        schema: str,
        key: str,
        old_value: str,
        new_value: str,
    ) -> None:
        super().__init__()

        self.old_entry = old_entry
        self.new_entry = new_entry
        self.schema = schema
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    @classmethod
    def create_from_entries(
        cls,
        old_entry: MapConfigEntry[YamlSerializable],
        new_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(new_entry.path) == 2, \
            f'Expected path length 2 (schema, key), got {len(new_entry.path)}: {new_entry.path}'
        assert new_entry.path == old_entry.path
        schema, key = new_entry.path
        encoded_old_value = encode_value(old_entry.value)
        encoded_new_value = encode_value(new_entry.value)

        return cls(
            old_entry,
            new_entry,
            schema,
            key,
            encoded_old_value,
            encoded_new_value,
        )

    def get_description(self) -> str:
        return f'Update gsettings: {self.key} = {self.old_entry.value} -> {self.new_entry.value}'

    def get_old_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.old_entry

    def get_new_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = encode_value(self.new_value)
        executor.command(
            'gsettings',
            'set',
            self.schema,
            self.key,
            encoded_value,
        )


class GSettingsRemoveAction(DomainAction):
    """
    Action to remove an existing gsettings value (reset to default).

    Note that this "unsets" the value, it does not revert to a value previously set by this tool.
    """

    def __init__(
        self,
        old_entry: MapConfigEntry[YamlSerializable],
        schema: str,
        key: str,
        old_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.old_entry = old_entry
        self.schema = schema
        self.key = key
        self.old_value = old_value

    @classmethod
    def create_from_entry(
        cls,
        old_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(old_entry.path) == 2, \
            f'Expected path length 2 (schema, key), got {len(old_entry.path)}: {old_entry.path}'
        schema, key = old_entry.path
        encoded_value = encode_value(old_entry.value)

        return cls(old_entry, schema, key, encoded_value)

    def get_description(self) -> str:
        return f'Remove gsettings: {self.key} = {self.old_entry.value}'

    def get_old_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.old_entry

    def get_new_entry(self) -> None:
        return None

    def run(self, executor: SystemExecutor) -> None:
        executor.command('gsettings', 'reset', self.schema, self.key)
