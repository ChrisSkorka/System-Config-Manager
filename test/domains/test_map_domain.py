# pyright: strict

from dataclasses import dataclass

from sysconf.config.domains import DomainAction
from sysconf.domains.list_domain import ListConfigEntry, ListDomain
from sysconf.domains.map_domain import MapConfigEntry, MapDomain
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.test_case import TestCase


def add_action_factory(new_entry: MapConfigEntry[str]) -> DomainAction:
    return MockDomainAction(f'add {new_entry.value}')


def other_add_action_factory(new_entry: MapConfigEntry[str]) -> DomainAction:
    return MockDomainAction(f'other add {new_entry.value}')


def update_action_factory(
    old_entry: MapConfigEntry[str],
    new_entry: MapConfigEntry[str],
) -> DomainAction:
    return MockDomainAction(f'update {old_entry.value} -> {new_entry.value}')


def remove_action_factory(old_entry: MapConfigEntry[str]) -> DomainAction:
    return MockDomainAction(f'remove {old_entry.value}')


def list_add_action_factory(new_entry: ListConfigEntry) -> DomainAction:
    return MockDomainAction(f'add {new_entry.value}')


def list_remove_action_factory(old_entry: ListConfigEntry) -> DomainAction:
    return MockDomainAction(f'remove {old_entry.value}')


def make_map_domain(key: str, path_depth: int) -> MapDomain[str]:
    return MapDomain[str](
        key=key,
        path_depth=path_depth,
        get_value=str,
        add_action_factory=add_action_factory,
        update_action_factory=update_action_factory,
        remove_action_factory=remove_action_factory,
    )


SETTINGS_DOMAIN = make_map_domain('settings', 1)
OTHER_DOMAIN = make_map_domain('other', 1)
LIST_DOMAIN = ListDomain(
    key='settings',
    path_depth=1,
    get_value=str,
    add_action_factory=list_add_action_factory,
    remove_action_factory=list_remove_action_factory,
)


class TestMapDomain(TestCase):
    """Test MapDomain equality."""

    @dataclass
    class EqualityDataset:
        input_domain: MapDomain[str]
        input_other: object
        expected_equal: bool

    @datasets({
        'same key, depth and functions': EqualityDataset(
            input_domain=make_map_domain('settings', 1),
            input_other=make_map_domain('settings', 1),
            expected_equal=True,
        ),
        'different key': EqualityDataset(
            input_domain=make_map_domain('settings', 1),
            input_other=make_map_domain('other', 1),
            expected_equal=False,
        ),
        'different path depth': EqualityDataset(
            input_domain=make_map_domain('settings', 1),
            input_other=make_map_domain('settings', 2),
            expected_equal=False,
        ),
        'different action factory': EqualityDataset(
            input_domain=make_map_domain('settings', 1),
            input_other=MapDomain[str](
                key='settings',
                path_depth=1,
                get_value=str,
                add_action_factory=other_add_action_factory,
                update_action_factory=update_action_factory,
                remove_action_factory=remove_action_factory,
            ),
            expected_equal=False,
        ),
        'not a map domain': EqualityDataset(
            input_domain=make_map_domain('settings', 1),
            input_other=LIST_DOMAIN,
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that domains compare by key, depth and their functions."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_domain, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_domain, dataset.input_other)


class TestMapConfigEntry(TestCase):
    """Test MapConfigEntry equality."""

    @dataclass
    class EqualityDataset:
        input_entry: MapConfigEntry[str]
        input_other: object
        expected_equal: bool

    @datasets({
        'identical entries': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            expected_equal=True,
        ),
        'same domain key from another domain instance': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=MapConfigEntry(
                make_map_domain('settings', 1),
                ('key',),
                'value',
            ),
            expected_equal=True,
        ),
        'different value': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'other'),
            expected_equal=False,
        ),
        'different path': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=MapConfigEntry(SETTINGS_DOMAIN, ('other',), 'value'),
            expected_equal=False,
        ),
        'different domain key': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=MapConfigEntry(OTHER_DOMAIN, ('key',), 'value'),
            expected_equal=False,
        ),
        'not equal to list entry': EqualityDataset(
            input_entry=MapConfigEntry(SETTINGS_DOMAIN, ('key',), 'value'),
            input_other=ListConfigEntry(LIST_DOMAIN, ('key',), 'value'),
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that entries compare by domain key, path and value."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_entry, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_entry, dataset.input_other)
