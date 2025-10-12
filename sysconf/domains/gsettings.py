# pyright: strict

from sysconf.config.domains import DomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.dconf import MapDomain, encode_value
from sysconf.system.executor import SystemExecutor

GSettingPath = tuple[str, str]  # (schema, key)


def create_gsettings_domain() -> MapDomain[YamlSerializable]:
    """
    Create a MapDomain configured to parse, manage, and generate actions for 
    gsettings settings (gnome).
    """

    def add_action_factory(path: tuple[str, ...], new_value: YamlSerializable) -> GSettingsAddAction:
        assert len(path) == 2
        return GSettingsAddAction(
            path[0],
            path[1],
            new_value,
        )

    def update_action_factory(path: tuple[str, ...], old_value: YamlSerializable, new_value: YamlSerializable) -> GSettingsUpdateAction:
        assert len(path) == 2
        return GSettingsUpdateAction(
            path[0],
            path[1],
            old_value,
            new_value,
        )

    def remove_action_factory(path: tuple[str, ...], old_value: YamlSerializable) -> GSettingsRemoveAction:
        assert len(path) == 2
        return GSettingsRemoveAction(
            path[0],
            path[1],
            old_value,
        )

    return MapDomain[YamlSerializable](
        'gsettings',
        add_action_factory=add_action_factory,
        update_action_factory=update_action_factory,
        remove_action_factory=remove_action_factory,
        get_value=lambda v: v,
    )


class GSettingsAddAction(DomainAction):
    """
    Action to add a new gsettings value.
    """

    def __init__(
        self,
        schema: str,
        key: str,
        new_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.schema = schema
        self.key = key
        self.new_value = new_value

    def get_description(self) -> str:
        return f'Add gsettings: {self.key} = {self.new_value}'

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = encode_value(self.new_value)
        executor.command(
            'gsettings',
            'set',
            self.schema,
            self.key,
            encoded_value,
        )


class GSettingsUpdateAction(DomainAction):
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
        super().__init__()

        self.schema = schema
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    def get_description(self) -> str:
        return f'Update gsettings: {self.key} = {self.old_value} -> {self.new_value}'

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
        schema: str,
        key: str,
        old_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.schema = schema
        self.key = key
        self.old_value = old_value

    def get_description(self) -> str:
        return f'Remove gsettings: {self.key} = {self.old_value}'

    def run(self, executor: SystemExecutor) -> None:
        executor.command('gsettings', 'reset', self.schema, self.key)
