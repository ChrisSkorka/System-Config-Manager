# pyright: strict

from dataclasses import dataclass
from unittest.mock import MagicMock

from sysconf.config.domains import DomainAction, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.list_domain import ListConfigEntry
from sysconf.domains.map_domain import MapConfigEntry
from sysconf.domains.shell_domains import (
    ShellAddAction,
    ShellRemoveAction,
    ShellScriptTemplate,
    ShellUpdateAction,
)
from sysconf.domains.user_domains import UserListDomain, UserMapDomain
from test.datasets import datasets
from test.system.mock_system_executor import MockSystemExecutor
from test.test_case import TestCase


PACKAGES_DOMAIN: UserListDomain = UserListDomain.create_from_specs(
    key='my-packages',
    path_depth=0,
    add_script='my-pm install $value',
    remove_script='my-pm remove $value',
)

USER_GROUPS_DOMAIN: UserListDomain = UserListDomain.create_from_specs(
    key='user-groups',
    path_depth=1,
    add_script='usermod -aG "$value" "$key"',
    remove_script='gpasswd -d "$key" "$value"',
)

SETTINGS_DOMAIN: UserMapDomain = UserMapDomain.create_from_specs(
    key='my-config',
    path_depth=1,
    add_script='my-cfg set "$key" "$value"',
    update_script='my-cfg set "$key" "$value"',
    remove_script='my-cfg unset "$key"',
)


class TestUserListDomain(TestCase):
    """Test that a user defined list domain delegates to its shell domain."""

    @dataclass
    class ParseDataset:
        fixture_domain: UserListDomain
        input_data: YamlSerializable
        expected_entries: tuple[tuple[tuple[str, ...], str], ...]

    @datasets({
        'flat list': ParseDataset(
            fixture_domain=PACKAGES_DOMAIN,
            input_data=['git', 'vim'],
            expected_entries=(
                ((), 'git'),
                ((), 'vim'),
            ),
        ),
        'no data': ParseDataset(
            fixture_domain=PACKAGES_DOMAIN,
            input_data=None,
            expected_entries=(),
        ),
        'keyed list': ParseDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_data={'alice': ['docker', 'sudo']},
            expected_entries=(
                (('alice',), 'docker'),
                (('alice',), 'sudo'),
            ),
        ),
    })
    def test_get_config_entries(self, dataset: ParseDataset) -> None:
        """Test that data is parsed into entries with the right paths/values."""

        # Act
        actual = tuple(
            (entry.path, entry.value)
            for entry in dataset.fixture_domain.get_config_entries(
                dataset.input_data,
            )
        )

        # Assert
        self.assertEqual(actual, dataset.expected_entries)
        self.assertEqual(
            dataset.fixture_domain.get_key(),
            dataset.fixture_domain.key,
        )

    @dataclass
    class RenderDataset:
        fixture_domain: UserListDomain
        input_data: YamlSerializable

    @datasets({
        'flat list': RenderDataset(
            fixture_domain=PACKAGES_DOMAIN,
            input_data=['git', 'vim'],
        ),
        'keyed list': RenderDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_data={'alice': ['docker', 'sudo']},
        ),
    })
    def test_render_config_entries_round_trip(
        self,
        dataset: RenderDataset,
    ) -> None:
        """Test that parsing then rendering reproduces the original data."""

        # Act
        entries = dataset.fixture_domain.get_config_entries(dataset.input_data)
        actual = dataset.fixture_domain.render_config_entries(entries)

        # Assert
        self.assertEqual(actual, dataset.input_data)

    @dataclass
    class ActionDataset:
        fixture_domain: UserListDomain
        input_old_entry: DomainConfigEntry | None
        input_new_entry: DomainConfigEntry | None
        expected_action: DomainAction
        expected_script: str

    @datasets({
        'add': ActionDataset(
            fixture_domain=PACKAGES_DOMAIN,
            input_old_entry=None,
            input_new_entry=ListConfigEntry(
                PACKAGES_DOMAIN.list_domain, (), 'git'),
            expected_action=ShellAddAction(
                'my-packages',
                ListConfigEntry(PACKAGES_DOMAIN.list_domain, (), 'git'),
                ShellScriptTemplate('my-pm install $value'),
            ),
            expected_script='my-pm install git',
        ),
        'remove': ActionDataset(
            fixture_domain=PACKAGES_DOMAIN,
            input_old_entry=ListConfigEntry(
                PACKAGES_DOMAIN.list_domain, (), 'git'),
            input_new_entry=None,
            expected_action=ShellRemoveAction(
                'my-packages',
                ListConfigEntry(PACKAGES_DOMAIN.list_domain, (), 'git'),
                ShellScriptTemplate('my-pm remove $value'),
            ),
            expected_script='my-pm remove git',
        ),
        'add with a keyed path': ActionDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_old_entry=None,
            input_new_entry=ListConfigEntry(
                USER_GROUPS_DOMAIN.list_domain, ('alice',), 'docker'),
            expected_action=ShellAddAction(
                'user-groups',
                ListConfigEntry(
                    USER_GROUPS_DOMAIN.list_domain, ('alice',), 'docker'),
                ShellScriptTemplate('usermod -aG "$value" "$key"'),
            ),
            expected_script='usermod -aG "docker" "alice"',
        ),
    })
    def test_get_action(self, dataset: ActionDataset) -> None:
        """Test that the delegated action is built and runs the right script."""

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

    @dataclass
    class SpecDataset:
        fixture_domain: UserListDomain
        expected_rendered: YamlSerializable

    @datasets({
        'flat list domain': SpecDataset(
            fixture_domain=PACKAGES_DOMAIN,
            expected_rendered={
                'depth': 0,
                'add': 'my-pm install $value',
                'remove': 'my-pm remove $value',
            },
        ),
        'keyed list domain': SpecDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            expected_rendered={
                'depth': 1,
                'add': 'usermod -aG "$value" "$key"',
                'remove': 'gpasswd -d "$key" "$value"',
            },
        ),
    })
    def test_render(self, dataset: SpecDataset) -> None:
        """Test that the domain renders back to its user defined spec."""

        # Act & Assert
        self.assertEqual(
            dataset.fixture_domain.render(),
            dataset.expected_rendered,
        )


class TestUserMapDomain(TestCase):
    """Test that a user defined map domain delegates to its shell domain."""

    @dataclass
    class ParseDataset:
        fixture_domain: UserMapDomain
        input_data: YamlSerializable
        expected_entries: tuple[tuple[tuple[str, ...], str], ...]

    @datasets({
        'flat map': ParseDataset(
            fixture_domain=SETTINGS_DOMAIN,
            input_data={'user.name': 'alice', 'user.email': 'a@b.com'},
            expected_entries=(
                (('user.name',), 'alice'),
                (('user.email',), 'a@b.com'),
            ),
        ),
        'no data': ParseDataset(
            fixture_domain=SETTINGS_DOMAIN,
            input_data=None,
            expected_entries=(),
        ),
        'values are coerced to strings': ParseDataset(
            fixture_domain=SETTINGS_DOMAIN,
            input_data={'count': 4},
            expected_entries=(
                (('count',), '4'),
            ),
        ),
    })
    def test_get_config_entries(self, dataset: ParseDataset) -> None:
        """Test that data is parsed into entries with the right paths/values."""

        # Act
        actual = tuple(
            (entry.path, entry.value)
            for entry in dataset.fixture_domain.get_config_entries(
                dataset.input_data,
            )
        )

        # Assert
        self.assertEqual(actual, dataset.expected_entries)
        self.assertEqual(
            dataset.fixture_domain.get_key(),
            dataset.fixture_domain.key,
        )

    def test_render_config_entries_round_trip(self) -> None:
        """Test that parsing then rendering reproduces the original data."""

        # Arrange
        data: YamlSerializable = {'user.name': 'alice', 'user.email': 'a@b.com'}

        # Act
        entries = SETTINGS_DOMAIN.get_config_entries(data)
        actual = SETTINGS_DOMAIN.render_config_entries(entries)

        # Assert
        self.assertEqual(actual, data)

    @dataclass
    class ActionDataset:
        input_old_entry: DomainConfigEntry | None
        input_new_entry: DomainConfigEntry | None
        expected_action: DomainAction
        expected_script: str

    @datasets({
        'add': ActionDataset(
            input_old_entry=None,
            input_new_entry=MapConfigEntry(
                SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
            expected_action=ShellAddAction(
                'my-config',
                MapConfigEntry(
                    SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
                ShellScriptTemplate('my-cfg set "$key" "$value"'),
            ),
            expected_script='my-cfg set "user.name" "alice"',
        ),
        'update': ActionDataset(
            input_old_entry=MapConfigEntry(
                SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
            input_new_entry=MapConfigEntry(
                SETTINGS_DOMAIN.map_domain, ('user.name',), 'bob'),
            expected_action=ShellUpdateAction(
                'my-config',
                MapConfigEntry(
                    SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
                MapConfigEntry(
                    SETTINGS_DOMAIN.map_domain, ('user.name',), 'bob'),
                ShellScriptTemplate('my-cfg set "$key" "$value"'),
            ),
            expected_script='my-cfg set "user.name" "bob"',
        ),
        'remove': ActionDataset(
            input_old_entry=MapConfigEntry(
                SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
            input_new_entry=None,
            expected_action=ShellRemoveAction(
                'my-config',
                MapConfigEntry(
                    SETTINGS_DOMAIN.map_domain, ('user.name',), 'alice'),
                ShellScriptTemplate('my-cfg unset "$key"'),
            ),
            expected_script='my-cfg unset "user.name"',
        ),
    })
    def test_get_action(self, dataset: ActionDataset) -> None:
        """Test that the delegated action is built and runs the right script."""

        # Arrange
        executor = MockSystemExecutor()

        # Act
        actual = SETTINGS_DOMAIN.get_action(
            dataset.input_old_entry,
            dataset.input_new_entry,
        )
        actual.run(executor)

        # Assert
        self.assertEqual(actual, dataset.expected_action)

        assert isinstance(executor.shell_mock, MagicMock)
        executor.shell_mock.assert_called_once_with(dataset.expected_script)

    def test_render_omits_the_update_script(self) -> None:
        """
        Test the rendered user defined map domain spec.

        Note: `render` currently omits the `update` script, so a map domain does
        not survive a round trip through the current config.
        """

        # Act & Assert
        self.assertEqual(
            SETTINGS_DOMAIN.render(),
            {
                'depth': 1,
                'add': 'my-cfg set "$key" "$value"',
                'remove': 'my-cfg unset "$key"',
            },
        )
