# pyright: strict

from typing import Self
from sysconf.config.domains import DomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from sysconf.system.executor import SystemExecutor


def create_dconf_domain() -> MapDomain[YamlSerializable]:
    """
    Create a MapDomain configured to parse, manage, and generate actions for 
    dconf settings.
    """

    def add_action_factory(new_entry: MapConfigEntry[YamlSerializable]) -> DConfAddAction:
        return DConfAddAction.create_from_entry(new_entry)

    def update_action_factory(
        old_entry: MapConfigEntry[YamlSerializable],
        new_entry: MapConfigEntry[YamlSerializable],
    ) -> DConfUpdateAction:
        return DConfUpdateAction.create_from_entries(old_entry, new_entry)

    def remove_action_factory(old_entry: MapConfigEntry[YamlSerializable]) -> DConfRemoveAction:
        return DConfRemoveAction.create_from_entry(old_entry)

    return MapDomain[YamlSerializable](
        'dconf',
        path_depth=1,
        get_value=lambda v: v,
        add_action_factory=add_action_factory,
        update_action_factory=update_action_factory,
        remove_action_factory=remove_action_factory,
    )


def encode_value(value: YamlSerializable) -> str:
    """
    Encode a YamlSerializable value into a dconf compatible string
    """

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
            return f"[{', '.join(encode_value(v) for v in l)}]"
        case d if isinstance(d, dict):
            key_value_pairs = (
                f'"{k}": {encode_value(v)}' for k, v in d.items())
            return f"{{ {', '.join(key_value_pairs)} }}"
        case _:
            assert False, f'Unsupported value type {type(value)}'


class DConfAddAction(DomainAction):
    """
    Action to add a new dconf value.
    """

    def __init__(
        self,
        new_entry: MapConfigEntry[YamlSerializable],
        path: str,
        value: str,
    ) -> None:
        super().__init__()

        self.new_entry = new_entry
        self.path = path
        self.value = value

    @classmethod
    def create_from_entry(
        cls,
        new_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(new_entry.path) == 1
        path = new_entry.path[0]
        encoded_value = encode_value(new_entry.value)

        return cls(new_entry, path, encoded_value)

    def get_description(self) -> str:
        return f'Add dconf: {self.path} = {self.new_entry.value}'

    def get_old_entry(self) -> None:
        return None

    def get_new_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        executor.command('dconf', 'write', self.path, self.value)


class DConfUpdateAction(DomainAction):
    """
    Action to update an existing dconf value.
    """

    def __init__(
        self,
        old_entry: MapConfigEntry[YamlSerializable],
        new_entry: MapConfigEntry[YamlSerializable],
        path: str,
        old_value: str,
        new_value: str,
    ) -> None:
        super().__init__()

        self.old_entry = old_entry
        self.new_entry = new_entry
        self.path = path
        self.old_value = old_value
        self.new_value = new_value

    @classmethod
    def create_from_entries(
        cls,
        old_entry: MapConfigEntry[YamlSerializable],
        new_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(new_entry.path) == 1
        assert new_entry.path == old_entry.path
        path = new_entry.path[0]
        encoded_old_value = encode_value(old_entry.value)
        encoded_new_value = encode_value(new_entry.value)

        return cls(old_entry, new_entry, path, encoded_old_value, encoded_new_value)

    def get_description(self) -> str:
        return f'Update dconf: {self.path} = {self.old_entry.value} -> {self.new_entry.value}'

    def get_old_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.old_entry

    def get_new_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        executor.command('dconf', 'write', self.path, self.new_value)


class DConfRemoveAction(DomainAction):
    """
    Action to remove an existing dconf value (reset to default).

    Note that this "unsets" the value, it does not revert to a value previously set by this tool.
    """

    def __init__(
        self,
        old_entry: MapConfigEntry[YamlSerializable],
        path: str,
        old_value: str,
    ) -> None:
        super().__init__()

        self.old_entry = old_entry
        self.path = path
        self.old_value = old_value

    @classmethod
    def create_from_entry(
        cls,
        old_entry: MapConfigEntry[YamlSerializable],
    ) -> Self:
        assert len(old_entry.path) == 1
        path = old_entry.path[0]
        encoded_value = encode_value(old_entry.value)

        return cls(old_entry, path, encoded_value)

    def get_description(self) -> str:
        return f'Remove dconf: {self.path} = {self.old_entry.value}'

    def get_old_entry(self) -> MapConfigEntry[YamlSerializable]:
        return self.old_entry

    def get_new_entry(self) -> None:
        return None

    def run(self, executor: SystemExecutor) -> None:
        executor.command('dconf', 'reset', self.path)
