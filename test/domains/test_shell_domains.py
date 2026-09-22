# pyright: strict

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

from sysconf.config.domains import DomainAction
from sysconf.domains.list_domain import ListConfigEntry, ListDomain
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from sysconf.domains.shell_domains import (
    ShellAddAction,
    ShellRemoveAction,
    ShellScriptTemplate,
    ShellUpdateAction,
    create_list_shell_domain,
    create_map_shell_domain,
)
from test.datasets import datasets
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


APT_DOMAIN: ListDomain = create_list_shell_domain(
    key='apt',
    path_depth=0,
    add_script='sudo apt install -y $value',
    remove_script='sudo apt remove -y $value',
)

USER_GROUPS_DOMAIN: ListDomain = create_list_shell_domain(
    key='user-groups',
    path_depth=1,
    add_script='sudo usermod -aG "$value" "$key"',
    remove_script='echo "not implemented"; exit 1;',
)

GIT_CONFIG_DOMAIN: MapDomain[str] = create_map_shell_domain(
    key='git-config-global',
    path_depth=1,
    add_script='git config --global "$key" "$value"',
    update_script='git config --global "$key" "$value"',
    remove_script='git config --global --unset "$key"',
)


def list_entry(
    domain: ListDomain,
    path: tuple[str, ...],
    value: str,
) -> ListConfigEntry:
    return ListConfigEntry(domain=domain, path=path, value=value)


def map_entry(
    domain: MapDomain[str],
    path: tuple[str, ...],
    value: str,
) -> MapConfigEntry[str]:
    return MapConfigEntry(domain=domain, path=path, value=value)


class TestShellScriptTemplate(TestCase):
    """Test shell script template equality, path variables and interpolation."""

    @dataclass
    class EqualityDataset:
        input_template: ShellScriptTemplate
        input_other: Any
        expected_equal: bool

    @datasets({
        'identical scripts': EqualityDataset(
            input_template=ShellScriptTemplate('echo "hello"'),
            input_other=ShellScriptTemplate('echo "hello"'),
            expected_equal=True,
        ),
        'different scripts': EqualityDataset(
            input_template=ShellScriptTemplate('echo "hello"'),
            input_other=ShellScriptTemplate('echo "world"'),
            expected_equal=False,
        ),
        'empty scripts': EqualityDataset(
            input_template=ShellScriptTemplate(''),
            input_other=ShellScriptTemplate(''),
            expected_equal=True,
        ),
        'not equal to string': EqualityDataset(
            input_template=ShellScriptTemplate('echo "hello"'),
            input_other='echo "hello"',
            expected_equal=False,
        ),
        'not equal to None': EqualityDataset(
            input_template=ShellScriptTemplate('echo "hello"'),
            input_other=None,
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that templates compare by script content only."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_template, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_template, dataset.input_other)

    @dataclass
    class PathVariablesDataset:
        input_template: ShellScriptTemplate
        input_path: tuple[str, ...]
        expected_variables: dict[str, str]

    @datasets({
        'empty path': PathVariablesDataset(
            input_template=ShellScriptTemplate('echo $value'),
            input_path=(),
            expected_variables={},
        ),
        'single key': PathVariablesDataset(
            input_template=ShellScriptTemplate('echo $key'),
            input_path=('alice',),
            expected_variables={
                '$key1': 'alice',
                '$key': 'alice',
            },
        ),
        'two keys': PathVariablesDataset(
            input_template=ShellScriptTemplate('echo $key1 $key2'),
            input_path=('root', '/root/dir'),
            expected_variables={
                '$key1': 'root',
                '$key2': '/root/dir',
                '$key': 'root',
            },
        ),
        'three keys': PathVariablesDataset(
            input_template=ShellScriptTemplate('echo $key1 $key2 $key3'),
            input_path=('a', 'b', 'c'),
            expected_variables={
                '$key1': 'a',
                '$key2': 'b',
                '$key3': 'c',
                '$key': 'a',
            },
        ),
    })
    def test_get_path_variables(self, dataset: PathVariablesDataset) -> None:
        """Test that path items map to 1-indexed $keyN variables, $key aliasing the first."""

        # Act
        actual = dataset.input_template.get_path_variables(dataset.input_path)

        # Assert
        self.assertEqual(actual, dataset.expected_variables)

    @dataclass
    class InterpolateDataset:
        input_template: ShellScriptTemplate
        input_variables: dict[str, str]
        expected_script: str

    @datasets({
        'no variables': InterpolateDataset(
            input_template=ShellScriptTemplate('sudo apt update'),
            input_variables={},
            expected_script='sudo apt update',
        ),
        'single value': InterpolateDataset(
            input_template=ShellScriptTemplate('sudo apt install -y $value'),
            input_variables={'$value': 'git'},
            expected_script='sudo apt install -y git',
        ),
        'repeated variable': InterpolateDataset(
            input_template=ShellScriptTemplate('rm -f $key; ln -sf $value $key'),
            input_variables={'$key': '~/.bashrc', '$value': './bashrc'},
            expected_script='rm -f ~/.bashrc; ln -sf ./bashrc ~/.bashrc',
        ),
        'keyed variables replaced before bare key': InterpolateDataset(
            input_template=ShellScriptTemplate('echo $key1 $key2 $key'),
            input_variables={'$key1': 'a', '$key2': 'b', '$key': 'a'},
            expected_script='echo a b a',
        ),
        'old and new value': InterpolateDataset(
            input_template=ShellScriptTemplate('echo "$old_value -> $new_value"'),
            input_variables={'$old_value': 'v1', '$new_value': 'v2'},
            expected_script='echo "v1 -> v2"',
        ),
        'multiline script': InterpolateDataset(
            input_template=ShellScriptTemplate('rm -f $key;\nln -sf $value $key;'),
            input_variables={'$key': '/tmp/a', '$value': '/tmp/b'},
            expected_script='rm -f /tmp/a;\nln -sf /tmp/b /tmp/a;',
        ),
        'unknown variable left as is': InterpolateDataset(
            input_template=ShellScriptTemplate('echo $unknown $value'),
            input_variables={'$value': 'x'},
            expected_script='echo $unknown x',
        ),
    })
    def test_get_interpolated_script(self, dataset: InterpolateDataset) -> None:
        """Test that each variable name is substituted with its value."""

        # Act
        actual = dataset.input_template.get_interpolated_script(
            dataset.input_variables,
        )

        # Assert
        self.assertEqual(actual, dataset.expected_script)


class TestShellAddAction(TestCase):
    """Test ShellAddAction description and execution."""

    @dataclass
    class AddDataset:
        input_action: ShellAddAction
        expected_description: str
        expected_script: str

    @datasets({
        'list domain without keys': AddDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_description='Add apt: git',
            expected_script='sudo apt install -y git',
        ),
        'list domain with one key': AddDataset(
            input_action=ShellAddAction(
                'user-groups',
                list_entry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
                ShellScriptTemplate('sudo usermod -aG "$value" "$key"'),
            ),
            expected_description='Add user-groups: alice = docker',
            expected_script='sudo usermod -aG "docker" "alice"',
        ),
        'map domain with one key': AddDataset(
            input_action=ShellAddAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_description='Add git-config-global: user.email = a@b.com',
            expected_script='git config --global "user.email" "a@b.com"',
        ),
        'new_value alias': AddDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'vim'),
                ShellScriptTemplate('echo $new_value'),
            ),
            expected_description='Add apt: vim',
            expected_script='echo vim',
        ),
    })
    def test_description_and_run(self, dataset: AddDataset) -> None:
        """Test that the add action describes itself and runs the interpolated script."""

        # Arrange
        action = dataset.input_action
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertIsNone(action.get_old_entry())
        self.assertEqual(action.get_new_entry(), action.new_entry)

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)

    @dataclass
    class EqualityDataset:
        input_action: ShellAddAction
        input_other: Any
        expected_equal: bool

    @datasets({
        'identical actions': EqualityDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            input_other=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_equal=True,
        ),
        'different key': EqualityDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            input_other=ShellAddAction(
                'snap',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_equal=False,
        ),
        'different entry value': EqualityDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            input_other=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'vim'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_equal=False,
        ),
        'not equal to remove action': EqualityDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            input_other=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_equal=False,
        ),
        'not equal to string': EqualityDataset(
            input_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            input_other='apt',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that add actions compare by key, entry and script template."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_action, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_action, dataset.input_other)


class TestShellUpdateAction(TestCase):
    """Test ShellUpdateAction description and execution."""

    @dataclass
    class UpdateDataset:
        input_action: ShellUpdateAction
        expected_description: str
        expected_script: str

    @datasets({
        'map domain value change': UpdateDataset(
            input_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'old@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'new@b.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_description='Update git-config-global: user.email = old@b.com -> new@b.com',
            expected_script='git config --global "user.email" "new@b.com"',
        ),
        'script using old and new value': UpdateDataset(
            input_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.name',), 'Old Name'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.name',), 'New Name'),
                ShellScriptTemplate('echo "$old_value => $new_value"'),
            ),
            expected_description='Update git-config-global: user.name = Old Name -> New Name',
            expected_script='echo "Old Name => New Name"',
        ),
    })
    def test_description_and_run(self, dataset: UpdateDataset) -> None:
        """Test that the update action runs the script with the new value."""

        # Arrange
        action = dataset.input_action
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertEqual(action.get_old_entry(), action.old_entry)
        self.assertEqual(action.get_new_entry(), action.new_entry)

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)

    @dataclass
    class EqualityDataset:
        input_action: ShellUpdateAction
        input_other: Any
        expected_equal: bool

    @datasets({
        'identical actions': EqualityDataset(
            input_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            input_other=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_equal=True,
        ),
        'different old entry': EqualityDataset(
            input_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            input_other=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'x@y.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_equal=False,
        ),
        'not equal to none': EqualityDataset(
            input_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            input_other=None,
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that update actions compare by key, both entries and template."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_action, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_action, dataset.input_other)


class TestShellRemoveAction(TestCase):
    """Test ShellRemoveAction description and execution."""

    @dataclass
    class RemoveDataset:
        input_action: ShellRemoveAction
        expected_description: str
        expected_script: str

    @datasets({
        'list domain without keys': RemoveDataset(
            input_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            expected_description='Remove apt: git',
            expected_script='sudo apt remove -y git',
        ),
        'map domain with one key': RemoveDataset(
            input_action=ShellRemoveAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                ShellScriptTemplate('git config --global --unset "$key"'),
            ),
            expected_description='Remove git-config-global: user.email = a@b.com',
            expected_script='git config --global --unset "user.email"',
        ),
        'script using old_value': RemoveDataset(
            input_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'vim'),
                ShellScriptTemplate('echo removing $old_value'),
            ),
            expected_description='Remove apt: vim',
            expected_script='echo removing vim',
        ),
    })
    def test_description_and_run(self, dataset: RemoveDataset) -> None:
        """Test that the remove action runs the script with the old value."""

        # Arrange
        action = dataset.input_action
        executor = MockSystemExecutor()

        # Act
        action.run(executor)

        # Assert
        self.assertEqual(action.get_description(), dataset.expected_description)
        self.assertEqual(action.get_old_entry(), action.old_entry)
        self.assertIsNone(action.get_new_entry())

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)

    @dataclass
    class EqualityDataset:
        input_action: ShellRemoveAction
        input_other: Any
        expected_equal: bool

    @datasets({
        'identical actions': EqualityDataset(
            input_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            input_other=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            expected_equal=True,
        ),
        'different template': EqualityDataset(
            input_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            input_other=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt purge -y $value'),
            ),
            expected_equal=False,
        ),
        'not equal to int': EqualityDataset(
            input_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            input_other=42,
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that remove actions compare by key, entry and script template."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_action, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_action, dataset.input_other)


class TestCreateListShellDomain(TestCase):
    """Test that the list domain factory wires up the correct shell actions."""

    @dataclass
    class FactoryDataset:
        fixture_domain: ListDomain
        input_old_entry: ListConfigEntry | None
        input_new_entry: ListConfigEntry | None
        expected_action: DomainAction
        expected_script: str

    @datasets({
        'add': FactoryDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=None,
            input_new_entry=list_entry(APT_DOMAIN, (), 'git'),
            expected_action=ShellAddAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt install -y $value'),
            ),
            expected_script='sudo apt install -y git',
        ),
        'remove': FactoryDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=list_entry(APT_DOMAIN, (), 'git'),
            input_new_entry=None,
            expected_action=ShellRemoveAction(
                'apt',
                list_entry(APT_DOMAIN, (), 'git'),
                ShellScriptTemplate('sudo apt remove -y $value'),
            ),
            expected_script='sudo apt remove -y git',
        ),
        'add with a keyed path': FactoryDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_old_entry=None,
            input_new_entry=list_entry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
            expected_action=ShellAddAction(
                'user-groups',
                list_entry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
                ShellScriptTemplate('sudo usermod -aG "$value" "$key"'),
            ),
            expected_script='sudo usermod -aG "docker" "alice"',
        ),
    })
    def test_get_action(self, dataset: FactoryDataset) -> None:
        """Test that get_action builds the expected action and script."""

        # Arrange
        executor = MockSystemExecutor()

        # Act
        actual = dataset.fixture_domain.get_action(
            dataset.input_old_entry,
            dataset.input_new_entry,
        )
        actual.run(executor)

        # Assert
        self.assertEqual(actual, dataset.expected_action)

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)


class TestCreateMapShellDomain(TestCase):
    """Test that the map domain factory wires up the correct shell actions."""

    @dataclass
    class FactoryDataset:
        fixture_domain: MapDomain[str]
        input_old_entry: MapConfigEntry[str] | None
        input_new_entry: MapConfigEntry[str] | None
        expected_action: DomainAction
        expected_script: str

    @datasets({
        'add': FactoryDataset(
            fixture_domain=GIT_CONFIG_DOMAIN,
            input_old_entry=None,
            input_new_entry=map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
            expected_action=ShellAddAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_script='git config --global "user.email" "a@b.com"',
        ),
        'update': FactoryDataset(
            fixture_domain=GIT_CONFIG_DOMAIN,
            input_old_entry=map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
            input_new_entry=map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
            expected_action=ShellUpdateAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'c@d.com'),
                ShellScriptTemplate('git config --global "$key" "$value"'),
            ),
            expected_script='git config --global "user.email" "c@d.com"',
        ),
        'remove': FactoryDataset(
            fixture_domain=GIT_CONFIG_DOMAIN,
            input_old_entry=map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
            input_new_entry=None,
            expected_action=ShellRemoveAction(
                'git-config-global',
                map_entry(GIT_CONFIG_DOMAIN, ('user.email',), 'a@b.com'),
                ShellScriptTemplate('git config --global --unset "$key"'),
            ),
            expected_script='git config --global --unset "user.email"',
        ),
    })
    def test_get_action(self, dataset: FactoryDataset) -> None:
        """Test that get_action builds the expected action and script."""

        # Arrange
        executor = MockSystemExecutor()

        # Act
        actual = dataset.fixture_domain.get_action(
            dataset.input_old_entry,
            dataset.input_new_entry,
        )
        actual.run(executor)

        # Assert
        self.assertEqual(actual, dataset.expected_action)

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)
