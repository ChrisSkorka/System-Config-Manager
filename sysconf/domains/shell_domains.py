# pyright: strict

from sysconf.config.domains import DomainAction
from sysconf.domains.list_domain import ListConfigEntry, ListDomain
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from sysconf.system.executor import SystemExecutor


def create_list_shell_domain(
    key: str,
    path_depth: int,
    add_script: str,
    remove_script: str,
) -> ListDomain:

    def add_action_factory(new_entry: ListConfigEntry | MapConfigEntry[str]) -> ShellAddAction:
        return ShellAddAction(
            key,
            new_entry,
            ShellScriptTemplate(add_script),
        )

    def remove_action_factory(old_entry: ListConfigEntry | MapConfigEntry[str]) -> ShellRemoveAction:
        return ShellRemoveAction(
            key,
            old_entry,
            ShellScriptTemplate(remove_script),
        )

    return ListDomain(
        key,
        path_depth,
        str,
        add_action_factory,
        remove_action_factory,
    )


def create_map_shell_domain(
    key: str,
    path_depth: int,
    add_script: str,
    update_script: str,
    remove_script: str,
) -> MapDomain[str]:

    def add_action_factory(new_entry: MapConfigEntry[str]) -> ShellAddAction:
        return ShellAddAction(
            key,
            new_entry,
            ShellScriptTemplate(add_script),
        )

    def update_action_factory(
        old_entry: MapConfigEntry[str],
        new_entry: MapConfigEntry[str],
    ) -> ShellUpdateAction:
        return ShellUpdateAction(
            key,
            old_entry,
            new_entry,
            ShellScriptTemplate(update_script),
        )

    def remove_action_factory(old_entry: MapConfigEntry[str]) -> ShellRemoveAction:
        return ShellRemoveAction(
            key,
            old_entry,
            ShellScriptTemplate(remove_script),
        )

    return MapDomain[str](
        key=key,
        path_depth=path_depth,
        add_action_factory=add_action_factory,
        update_action_factory=update_action_factory,
        remove_action_factory=remove_action_factory,
        get_value=str,
    )


class ShellScriptTemplate:

    def __init__(self, script: str) -> None:
        super().__init__()

        self.script = script

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellScriptTemplate):
            return False

        return self.script == other.script

    def get_interpolated_script(
        self,
        variables: dict[str, str],
    ) -> str:
        # perform the interpolation, replacing variable names with values
        interpolated_script = self.script
        for name, value in variables.items():
            interpolated_script = interpolated_script.replace(name, value)

        return interpolated_script

    # todo: does this belong to a `ShellAction` class?
    def get_path_variables(self, path: tuple[str, ...]) -> dict[str, str]:
        # map keys/path items to variable names (1-indexed)
        variables: dict[str, str] = {
            f'$key{i+1}': key
            for i, key
            in enumerate(path)
        }

        # if there are keys, map the first to $key as well
        if len(path) > 0:
            variables['$key'] = path[0]

        return variables


class ShellAddAction(DomainAction):
    """
    Action to add an item to the domain.
    """

    def __init__(
        self,
        key: str,
        new_entry: ListConfigEntry | MapConfigEntry[str],
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.new_entry = new_entry
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellAddAction):
            return False

        return (
            self.key == other.key
            and self.new_entry == other.new_entry
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.new_entry.path) > 0:
            target = f'{'.'.join(self.new_entry.path)} = '

        return f'Add {self.key}: {target}{self.new_entry.value}'

    def get_old_entry(self) -> None:
        return None

    def get_new_entry(self) -> ListConfigEntry | MapConfigEntry[str]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.new_entry.path),
            '$value': self.new_entry.value,
            '$new_value': self.new_entry.value,
        }
        script = self.script_template.get_interpolated_script(variables)
        executor.shell(script)


class ShellUpdateAction(DomainAction):
    """
    Action to update an item in the domain.
    """

    def __init__(
        self,
        key: str,
        old_entry: ListConfigEntry | MapConfigEntry[str],
        new_entry: ListConfigEntry | MapConfigEntry[str],
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.old_entry = old_entry
        self.new_entry = new_entry
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellUpdateAction):
            return False

        return (
            self.key == other.key
            and self.old_entry == other.old_entry
            and self.new_entry == other.new_entry
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.new_entry.path) > 0:
            target = f'{'.'.join(self.new_entry.path)} = '

        return f'Update {self.key}: {target}{self.old_entry.value} -> {self.new_entry.value}'

    def get_old_entry(self) -> ListConfigEntry | MapConfigEntry[str]:
        return self.old_entry

    def get_new_entry(self) -> ListConfigEntry | MapConfigEntry[str]:
        return self.new_entry

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.new_entry.path),
            '$value': self.new_entry.value,
            '$new_value': self.new_entry.value,
            '$old_value': self.old_entry.value,
        }
        script = self.script_template.get_interpolated_script(variables)
        executor.shell(script)


class ShellRemoveAction(DomainAction):
    """
    Action to remove an item from the domain.
    """

    def __init__(
        self,
        key: str,
        old_entry: ListConfigEntry | MapConfigEntry[str],
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.old_entry = old_entry
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellRemoveAction):
            return False

        return (
            self.key == other.key
            and self.old_entry == other.old_entry
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.old_entry.path) > 0:
            target = f'{'.'.join(self.old_entry.path)} = '

        return f'Remove {self.key}: {target}{self.old_entry.value}'

    def get_old_entry(self) -> ListConfigEntry | MapConfigEntry[str]:
        return self.old_entry

    def get_new_entry(self) -> None:
        return None

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.old_entry.path),
            '$value': self.old_entry.value,
            '$old_value': self.old_entry.value,
        }
        script = self.script_template.get_interpolated_script(variables)
        executor.shell(script)
