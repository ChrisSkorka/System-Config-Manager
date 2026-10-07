# pyright: strict

from dataclasses import dataclass
from pathlib import PurePath
from typing import Callable

from sysconf.storage.defaults import Defaults
from sysconf.system.path_service import PathService
from test.datasets import datasets
from test.system.mock_path_service import MockPathService
from test.test_case import TestCase


class TestDefaults(TestCase):
    """Test the default paths derived from the user's home directory."""

    @dataclass
    class DefaultPathDataset:
        input_get_path: Callable[[Defaults], PurePath]
        expected_path: PurePath

    @datasets({
        'config dir': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_config_dir(),
            expected_path=PurePath(
                '/home/test-user/.config/system-config-manager',
            ),
        ),
        'old config path': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_old_config_path(),
            expected_path=PurePath(
                '/home/test-user/.config/system-config-manager/.history/current.yaml',
            ),
        ),
        'config location path': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_config_location_path(),
            expected_path=PurePath(
                '/home/test-user/.config/system-config-manager/config',
            ),
        ),
        'new config path': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_new_config_path(),
            expected_path=PurePath(
                '/home/test-user/.config/system-config-manager/config/config.yaml',
            ),
        ),
    })
    def test_default_paths(self, dataset: DefaultPathDataset) -> None:
        """Test that each default expands to the expected absolute path."""

        # Arrange
        path_service = MockPathService(home_dir='/home/test-user')
        defaults = Defaults(path_service)

        # Act
        actual = dataset.input_get_path(defaults)

        # Assert
        self.assertEqual(actual, dataset.expected_path)

    @dataclass
    class DerivedPathDataset:
        input_get_path: Callable[[Defaults], PurePath]
        expected_relative_path: PurePath

    @datasets({
        'old config path': DerivedPathDataset(
            input_get_path=lambda defaults: defaults.get_old_config_path(),
            expected_relative_path=PurePath('.history') / 'current.yaml',
        ),
        'config location path': DerivedPathDataset(
            input_get_path=lambda defaults: defaults.get_config_location_path(),
            expected_relative_path=PurePath('config'),
        ),
        'new config path': DerivedPathDataset(
            input_get_path=lambda defaults: defaults.get_new_config_path(),
            expected_relative_path=PurePath('config') / 'config.yaml',
        ),
    })
    def test_config_paths_are_derived_from_the_config_dir(
        self,
        dataset: DerivedPathDataset,
    ) -> None:
        """
        Test that the config paths sit at a fixed place under the config dir.

        This runs against the real home directory, so it holds wherever the
        config dir happens to resolve to.
        """

        # Arrange
        path_service = PathService()
        defaults = Defaults(path_service)

        # Act
        actual = dataset.input_get_path(defaults)

        # Assert
        self.assertEqual(
            actual.relative_to(defaults.get_config_dir()),
            dataset.expected_relative_path,
        )
