# pyright: strict

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from sysconf.utils.defaults import Defaults
from test.datasets import datasets
from test.test_case import TestCase


# A fixed home directory so the expanded paths are the same on every machine
HOME_DIRECTORY = '/home/test-user'
CONFIG_DIR = Path(HOME_DIRECTORY) / '.config' / 'system-config-manager'


class TestDefaults(TestCase):
    """Test the default paths derived from the user's home directory."""

    @dataclass
    class DefaultPathDataset:
        input_get_path: Callable[[Defaults], Path]
        expected_path: Path

    @datasets({
        'config dir': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_config_dir(),
            expected_path=CONFIG_DIR,
        ),
        'old config path': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_old_config_path(),
            expected_path=CONFIG_DIR / '.history' / 'current.yaml',
        ),
        'new config path': DefaultPathDataset(
            input_get_path=lambda defaults: defaults.get_new_config_path(),
            expected_path=CONFIG_DIR / 'config.yaml',
        ),
    })
    def test_default_paths(self, dataset: DefaultPathDataset) -> None:
        """Test that each default expands to the expected absolute path."""

        # Arrange
        defaults = Defaults()

        # Act
        with patch.dict(os.environ, {'HOME': HOME_DIRECTORY}):
            actual = dataset.input_get_path(defaults)

        # Assert
        self.assertEqual(actual, dataset.expected_path)

    @dataclass
    class DerivedPathDataset:
        input_get_path: Callable[[Defaults], Path]
        expected_relative_path: Path

    @datasets({
        'old config path': DerivedPathDataset(
            input_get_path=lambda defaults: defaults.get_old_config_path(),
            expected_relative_path=Path('.history') / 'current.yaml',
        ),
        'new config path': DerivedPathDataset(
            input_get_path=lambda defaults: defaults.get_new_config_path(),
            expected_relative_path=Path('config.yaml'),
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
        defaults = Defaults()

        # Act
        actual = dataset.input_get_path(defaults)

        # Assert
        self.assertEqual(
            actual.relative_to(defaults.get_config_dir()),
            dataset.expected_relative_path,
        )
