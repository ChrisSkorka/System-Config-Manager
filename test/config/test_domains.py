# pyright: strict

from dataclasses import dataclass
from typing import Any

from sysconf.config.domains import DomainAction
from test.datasets import datasets
from test.test_case import TestCase


class DummyDomainAction(DomainAction):
    """Minimal mock for testing concrete methods in DomainAction."""

    def __init__(self, description: str) -> None:
        self.description = description

    def get_description(self) -> str:
        return self.description

    def run(self, executor: Any) -> None:
        pass


class TestDomainAction(TestCase):
    """Test concrete methods in the abstract DomainAction class."""

    @dataclass
    class DomainActionDataset:
        input_description: str
        expected_str: str

    @datasets({
        'simple description': DomainActionDataset(
            input_description="Test action description",
            expected_str="Test action description",
        ),
        'empty description': DomainActionDataset(
            input_description="",
            expected_str="",
        ),
        'description with newlines': DomainActionDataset(
            input_description="Line 1\nLine 2\nLine 3",
            expected_str="Line 1\nLine 2\nLine 3",
        ),
        'description with special characters': DomainActionDataset(
            input_description="Update setting: value='test' (important)",
            expected_str="Update setting: value='test' (important)",
        ),
    })
    def test_str(self, dataset: DomainActionDataset):
        """Test that __str__ properly delegates to get_description()."""

        # Arrange
        action = DummyDomainAction(dataset.input_description)

        # Act
        result_str = str(action)

        # Assert
        self.assertEqual(result_str, dataset.expected_str)
