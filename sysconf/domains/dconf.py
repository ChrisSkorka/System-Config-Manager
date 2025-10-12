# pyright: strict

from sysconf.config.domains import DomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.map_domain import MapDomain
from sysconf.system.executor import SystemExecutor


def create_dconf_domain() -> MapDomain[str]:
    """
    Create a MapDomain configured to parse, manage, and generate actions for 
    dconf settings.
    """

    def add_action_factory(path: tuple[str, ...], new_value: YamlSerializable) -> DConfAddAction:
        assert len(path) == 1
        return DConfAddAction(
            path[0],
            new_value,
        )

    def update_action_factory(path: tuple[str, ...], old_value: YamlSerializable, new_value: YamlSerializable) -> DConfUpdateAction:
        assert len(path) == 1
        return DConfUpdateAction(
            path[0],
            old_value,
            new_value,
        )

    def remove_action_factory(path: tuple[str, ...], old_value: YamlSerializable) -> DConfRemoveAction:
        assert len(path) == 1
        return DConfRemoveAction(
            path[0],
            old_value,
        )

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
        path: str,
        new_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.path = path
        self.new_value = new_value

    def get_description(self) -> str:
        return f'Add dconf: {self.path} = {self.new_value}'

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = encode_value(self.new_value)
        executor.command('dconf', 'write', self.path, encoded_value)


class DConfUpdateAction(DomainAction):
    """
    Action to update an existing dconf value.
    """

    def __init__(
        self,
        path: str,
        old_value: YamlSerializable,
        new_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.path = path
        self.old_value = old_value
        self.new_value = new_value

    def get_description(self) -> str:
        return f'Update dconf: {self.path} = {self.old_value} -> {self.new_value}'

    def run(self, executor: SystemExecutor) -> None:
        encoded_value = encode_value(self.new_value)
        executor.command('dconf', 'write', self.path, encoded_value)


class DConfRemoveAction(DomainAction):
    """
    Action to remove an existing dconf value (reset to default).

    Note that this "unsets" the value, it does not revert to a value previously set by this tool.
    """

    def __init__(
        self,
        path: str,
        old_value: YamlSerializable,
    ) -> None:
        super().__init__()

        self.path = path
        self.old_value = old_value

    def get_description(self) -> str:
        return f'Remove dconf: {self.path} = {self.old_value}'

    def run(self, executor: SystemExecutor) -> None:
        executor.command('dconf', 'reset', self.path)
