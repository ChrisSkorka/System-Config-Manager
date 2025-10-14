# pyright: strict


from sysconf.config.domains import DomainAction
from sysconf.domains.list_domain import ListDomain
from sysconf.domains.map_domain import MapDomain
from sysconf.system.executor import SystemExecutor


def create_list_shell_domain(
    key: str,
    path_depth: int,
    add_script: str,
    remove_script: str,
) -> ListDomain:

    def add_action_factory(path: tuple[str, ...], item: str) -> ShellAddAction:
        return ShellAddAction(
            key,
            path,
            item,
            ShellScriptTemplate(add_script),
        )

    def remove_action_factory(path: tuple[str, ...], item: str) -> ShellRemoveAction:
        return ShellRemoveAction(
            key,
            path,
            item,
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

    def add_action_factory(path: tuple[str, ...], new_value: str) -> ShellAddAction:
        return ShellAddAction(
            key,
            path,
            new_value,
            ShellScriptTemplate(add_script),
        )

    def update_action_factory(path: tuple[str, ...], old_value: str, new_value: str) -> ShellUpdateAction:
        return ShellUpdateAction(
            key,
            path,
            old_value,
            new_value,
            ShellScriptTemplate(update_script),
        )

    def remove_action_factory(path: tuple[str, ...], old_value: str) -> ShellRemoveAction:
        return ShellRemoveAction(
            key,
            path,
            old_value,
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
        path: tuple[str, ...],
        value: str,
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.path = path
        self.value = value
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellAddAction):
            return False

        return (
            self.key == other.key
            and self.path == other.path
            and self.value == other.value
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.path) > 0:
            target = f'{'.'.join(self.path)} = '

        return f'Add {self.key}: {target}{self.value}'

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.path),
            '$value': self.value,
            '$new_value': self.value,
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
        path: tuple[str, ...],
        old_value: str,
        new_value: str,
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.path = path
        self.old_value = old_value
        self.new_value = new_value
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellUpdateAction):
            return False

        return (
            self.key == other.key
            and self.path == other.path
            and self.old_value == other.old_value
            and self.new_value == other.new_value
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.path) > 0:
            target = f'{'.'.join(self.path)} = '

        return f'Update {self.key}: {target}{self.old_value} -> {self.new_value}'

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.path),
            '$value': self.new_value,
            '$new_value': self.new_value,
            '$old_value': self.old_value,
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
        path: tuple[str, ...],
        value: str,
        script_template: ShellScriptTemplate,
    ) -> None:
        super().__init__()

        self.key = key
        self.path = path
        self.value = value
        self.script_template = script_template

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShellRemoveAction):
            return False

        return (
            self.key == other.key
            and self.path == other.path
            and self.value == other.value
            and self.script_template == other.script_template
        )

    def get_description(self) -> str:

        target: str = ''
        if len(self.path) > 0:
            target = f'{'.'.join(self.path)} = '

        return f'Remove {self.key}: {target}{self.value}'

    def run(self, executor: SystemExecutor) -> None:
        variables = {
            **self.script_template.get_path_variables(self.path),
            '$value': self.value,
            '$old_value': self.value,
        }
        script = self.script_template.get_interpolated_script(variables)
        executor.shell(script)
