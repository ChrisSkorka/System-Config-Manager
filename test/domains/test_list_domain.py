# pyright: strict

from dataclasses import dataclass
from typing import Any

from sysconf.config.domains import DomainAction, DomainConfigEntry, NoDomainAction
from sysconf.config.serialization import YamlSerializable
from sysconf.domains.list_domain import ListConfigEntry, ListDomain
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.test_case import TestCase


def add_action_factory(new_entry: ListConfigEntry) -> DomainAction:
    return MockDomainAction(f'add {new_entry.value}')


def remove_action_factory(old_entry: ListConfigEntry) -> DomainAction:
    return MockDomainAction(f'remove {old_entry.value}')


def make_list_domain(key: str, path_depth: int) -> ListDomain:
    return ListDomain(
        key=key,
        path_depth=path_depth,
        get_value=str,
        add_action_factory=add_action_factory,
        remove_action_factory=remove_action_factory,
    )


APT_DOMAIN: ListDomain = make_list_domain('apt', 0)
USER_GROUPS_DOMAIN: ListDomain = make_list_domain('user-groups', 1)
FILES_DOMAIN: ListDomain = make_list_domain('files', 2)

OTHER_DOMAIN: ListDomain = make_list_domain('snap', 0)

MAP_DOMAIN: MapDomain[str] = MapDomain[str](
    key='map',
    path_depth=1,
    get_value=str,
    add_action_factory=lambda new_entry: MockDomainAction('add'),
    update_action_factory=lambda old_entry, new_entry: MockDomainAction('update'),
    remove_action_factory=lambda old_entry: MockDomainAction('remove'),
)


class TestListDomain(TestCase):
    """Test parsing, rendering and action selection for list domains."""

    @dataclass
    class GetEntriesDataset:
        fixture_domain: ListDomain
        input_data: YamlSerializable
        expected_entries: tuple[ListConfigEntry, ...]

    @datasets({
        'none data': GetEntriesDataset(
            fixture_domain=APT_DOMAIN,
            input_data=None,
            expected_entries=(),
        ),
        'empty list': GetEntriesDataset(
            fixture_domain=APT_DOMAIN,
            input_data=[],
            expected_entries=(),
        ),
        'flat list': GetEntriesDataset(
            fixture_domain=APT_DOMAIN,
            input_data=['git', 'vim'],
            expected_entries=(
                ListConfigEntry(APT_DOMAIN, (), 'git'),
                ListConfigEntry(APT_DOMAIN, (), 'vim'),
            ),
        ),
        'flat list coerces values to strings': GetEntriesDataset(
            fixture_domain=APT_DOMAIN,
            input_data=[1, 2],
            expected_entries=(
                ListConfigEntry(APT_DOMAIN, (), '1'),
                ListConfigEntry(APT_DOMAIN, (), '2'),
            ),
        ),
        'one level of keys': GetEntriesDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_data={
                'alice': ['docker', 'sudo'],
                'bob': ['docker'],
            },
            expected_entries=(
                ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
                ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'sudo'),
                ListConfigEntry(USER_GROUPS_DOMAIN, ('bob',), 'docker'),
            ),
        ),
        'one level of keys with none value': GetEntriesDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_data={
                'alice': None,
                'bob': ['docker'],
            },
            expected_entries=(
                ListConfigEntry(USER_GROUPS_DOMAIN, ('bob',), 'docker'),
            ),
        ),
        'two levels of keys': GetEntriesDataset(
            fixture_domain=FILES_DOMAIN,
            input_data={
                'root': {
                    '/root/dir-1': ['a.txt', 'b.txt'],
                    '/root/dir-2': ['c.txt'],
                },
            },
            expected_entries=(
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-1'), 'a.txt'),
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-1'), 'b.txt'),
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-2'), 'c.txt'),
            ),
        ),
    })
    def test_get_config_entries(self, dataset: GetEntriesDataset) -> None:
        """Test that data is flattened into entries preserving document order."""

        # Act
        actual = tuple(dataset.fixture_domain.get_config_entries(dataset.input_data))

        # Assert
        self.assertEqual(actual, dataset.expected_entries)

    @dataclass
    class RenderDataset:
        fixture_domain: ListDomain
        input_entries: tuple[ListConfigEntry, ...]
        expected_data: YamlSerializable

    @datasets({
        'no keys, no entries': RenderDataset(
            fixture_domain=APT_DOMAIN,
            input_entries=(),
            expected_data=[],
        ),
        'no keys, several entries': RenderDataset(
            fixture_domain=APT_DOMAIN,
            input_entries=(
                ListConfigEntry(APT_DOMAIN, (), 'git'),
                ListConfigEntry(APT_DOMAIN, (), 'vim'),
            ),
            expected_data=['git', 'vim'],
        ),
        'one key, no entries': RenderDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_entries=(),
            expected_data={},
        ),
        'one key, several entries': RenderDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_entries=(
                ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
                ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'sudo'),
                ListConfigEntry(USER_GROUPS_DOMAIN, ('bob',), 'docker'),
            ),
            expected_data={
                'alice': ['docker', 'sudo'],
                'bob': ['docker'],
            },
        ),
        'two keys': RenderDataset(
            fixture_domain=FILES_DOMAIN,
            input_entries=(
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-1'), 'a.txt'),
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-1'), 'b.txt'),
                ListConfigEntry(FILES_DOMAIN, ('root', '/root/dir-2'), 'c.txt'),
            ),
            expected_data={
                'root': {
                    '/root/dir-1': ['a.txt', 'b.txt'],
                    '/root/dir-2': ['c.txt'],
                },
            },
        ),
    })
    def test_render_config_entries(self, dataset: RenderDataset) -> None:
        """Test that entries render back into the nested list structure."""

        # Act
        actual = dataset.fixture_domain.render_config_entries(dataset.input_entries)

        # Assert
        self.assertEqual(actual, dataset.expected_data)

    @dataclass
    class RoundTripDataset:
        fixture_domain: ListDomain
        input_data: YamlSerializable

    @datasets({
        'no keys': RoundTripDataset(
            fixture_domain=APT_DOMAIN,
            input_data=['git', 'vim'],
        ),
        'one key': RoundTripDataset(
            fixture_domain=USER_GROUPS_DOMAIN,
            input_data={'alice': ['docker', 'sudo'], 'bob': ['docker']},
        ),
        'two keys': RoundTripDataset(
            fixture_domain=FILES_DOMAIN,
            input_data={'root': {'/dir': ['a.txt', 'b.txt']}},
        ),
    })
    def test_round_trip(self, dataset: RoundTripDataset) -> None:
        """Test that parsing then rendering reproduces the original data."""

        # Act
        entries = dataset.fixture_domain.get_config_entries(dataset.input_data)
        actual = dataset.fixture_domain.render_config_entries(entries)

        # Assert
        self.assertEqual(actual, dataset.input_data)

    @dataclass
    class GetActionDataset:
        fixture_domain: ListDomain
        input_old_entry: DomainConfigEntry | None
        input_new_entry: DomainConfigEntry | None
        expected_action: DomainAction

    @datasets({
        'add when only new entry': GetActionDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=None,
            input_new_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            expected_action=MockDomainAction('add git'),
        ),
        'remove when only old entry': GetActionDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_new_entry=None,
            expected_action=MockDomainAction('remove git'),
        ),
    })
    def test_get_action(self, dataset: GetActionDataset) -> None:
        """Test that add and remove actions are produced from the factories."""

        # Act
        actual = dataset.fixture_domain.get_action(
            dataset.input_old_entry,
            dataset.input_new_entry,
        )

        # Assert
        self.assertEqual(actual, dataset.expected_action)

    def test_get_action_no_op_when_both_entries(self) -> None:
        """Test that an unchanged entry produces a no-op action."""

        # Arrange
        old_entry = ListConfigEntry(APT_DOMAIN, (), 'git')
        new_entry = ListConfigEntry(APT_DOMAIN, (), 'git')

        # Act
        actual = APT_DOMAIN.get_action(old_entry, new_entry)

        # Assert
        self.assertIsInstance(actual, NoDomainAction)
        self.assertEqual(actual.get_old_entry(), old_entry)
        self.assertEqual(actual.get_new_entry(), new_entry)
        self.assertEqual(actual.get_description(), 'No action required.')

    @dataclass
    class InvalidActionDataset:
        fixture_domain: ListDomain
        input_old_entry: DomainConfigEntry | None
        input_new_entry: DomainConfigEntry | None

    @datasets({
        'both entries none': InvalidActionDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=None,
            input_new_entry=None,
        ),
        'new entry is a map entry': InvalidActionDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=None,
            input_new_entry=MapConfigEntry(MAP_DOMAIN, ('key',), 'value'),
        ),
        'old entry is a map entry': InvalidActionDataset(
            fixture_domain=APT_DOMAIN,
            input_old_entry=MapConfigEntry(MAP_DOMAIN, ('key',), 'value'),
            input_new_entry=None,
        ),
    })
    def test_get_action_with_unsupported_entries(
        self,
        dataset: InvalidActionDataset,
    ) -> None:
        """Test that unsupported entry combinations raise an AssertionError."""

        # Act & Assert
        with self.assertRaises(AssertionError) as context:
            dataset.fixture_domain.get_action(
                dataset.input_old_entry,
                dataset.input_new_entry,
            )

        self.assertIn('unable to generate action', str(context.exception))


class TestListConfigEntry(TestCase):
    """Test ListConfigEntry identity, equality and representation."""

    @dataclass
    class EqualityDataset:
        input_entry: ListConfigEntry
        input_other: Any
        expected_equal: bool

    @datasets({
        'identical entries': EqualityDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_other=ListConfigEntry(APT_DOMAIN, (), 'git'),
            expected_equal=True,
        ),
        'different value': EqualityDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_other=ListConfigEntry(APT_DOMAIN, (), 'vim'),
            expected_equal=False,
        ),
        'different path': EqualityDataset(
            input_entry=ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
            input_other=ListConfigEntry(USER_GROUPS_DOMAIN, ('bob',), 'docker'),
            expected_equal=False,
        ),
        'different domain': EqualityDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_other=ListConfigEntry(OTHER_DOMAIN, (), 'git'),
            expected_equal=False,
        ),
        'not equal to map entry': EqualityDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_other=MapConfigEntry(MAP_DOMAIN, ('key',), 'git'),
            expected_equal=False,
        ),
        'not equal to string': EqualityDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            input_other='git',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that entries compare by domain, path and value."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_entry, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_entry, dataset.input_other)

    @dataclass
    class EntryDataset:
        input_entry: ListConfigEntry
        expected_id: tuple[str, ...]
        expected_domain: ListDomain
        expected_repr: str

    @datasets({
        'no keys': EntryDataset(
            input_entry=ListConfigEntry(APT_DOMAIN, (), 'git'),
            expected_id=('apt', 'git'),
            expected_domain=APT_DOMAIN,
            expected_repr="ListConfigEntry(apt, (), git)",
        ),
        'one key': EntryDataset(
            input_entry=ListConfigEntry(USER_GROUPS_DOMAIN, ('alice',), 'docker'),
            expected_id=('user-groups', 'alice', 'docker'),
            expected_domain=USER_GROUPS_DOMAIN,
            expected_repr="ListConfigEntry(user-groups, ('alice',), docker)",
        ),
        'two keys': EntryDataset(
            input_entry=ListConfigEntry(FILES_DOMAIN, ('root', '/dir'), 'a.txt'),
            expected_id=('files', 'root', '/dir', 'a.txt'),
            expected_domain=FILES_DOMAIN,
            expected_repr="ListConfigEntry(files, ('root', '/dir'), a.txt)",
        ),
    })
    def test_entry_properties(self, dataset: EntryDataset) -> None:
        """Test the entry id, domain and repr."""

        # Act & Assert
        self.assertEqual(dataset.input_entry.get_id(), dataset.expected_id)
        self.assertIs(dataset.input_entry.get_domain(), dataset.expected_domain)
        self.assertEqual(repr(dataset.input_entry), dataset.expected_repr)
