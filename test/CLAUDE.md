# Run Tests:

```sh
python3 -m unittest discover test
```

# Write Tests

## Principles

- data driven
  - Dataset `@dataclass`
  - `@datasets`
  - field prefixed with `fixture_`, `input_`, `expected`/`expected_`
  - prefer 'whole'/outer-level objects over just passing in inner parts
  - generally one test method (& many datasets) per tested method
    - except where we need to test returning & raising cases
    - except when different tests perform different sequences of actions that are unnatural to encode as data
- many data one test
- strong types
- dedent for multiline strings (avoid using `\n`)
- arrange, act, assert comments (strict)
- avoid standalone test functions, merge with other tests when possible
- avoid setUp unless it's large or paired with tearDown, prefer simple setups in tests
- prefer full equal check against entire result object rather than just checking types or vague properties
- don't built tests specifically for and exclusively around specific real world examples/problems, instead create generic scenarios/examples
- names
  - ClassName -> TestClassName
  - method_name -> test_method_name
    - when testing returning & raising cases with materially different bodies: test_method_name_returns & test_method_name_raises
  - (don't include test details or expectations in the class, method, or dataset entry names)

## Template

```py
# pyright: strict

from dataclasses import dataclass
from textwrap import dedent
from typing import Any

from test.datasets import datasets
from test.test_case import TestCase


# Placeholder for demonstration, not part of tests
class Dependency:
    pass

class SampleProcessor:
    def __init__(self, dependency: Dependency) -> None:
        self.dependency = dependency

    def process(self, value: str, option: bool = True) -> tuple[str, int]:
        return (f'{value} processed', 0)


class TestSampleDataDriven(TestCase):
    """Test sample functionality using data-driven approach."""

    @dataclass
    class SampleDataset:
        """Dataset for a single test case with strong typing."""
        fixture_dependency: Dependency  # Optional fixture data, use fixture_ prefix
        input_value: str  # Input data, use input_ prefix
        input_option: bool
        expected_result: str  # Expected output, use expected_ prefix
        expected_status: int

    @datasets({
        'simple case': SampleDataset(
            fixture_dependency=Dependency(),
            input_value='hello',
            input_option=True,
            expected_result='hello processed',
            expected_status=0,
        ),
        'multiline input with dedent': SampleDataset(
            fixture_dependency=Dependency(),
            input_value=dedent('''
                line 1
                line 2
                line 3
            ''').strip(),
            input_option=False,
            expected_result=dedent('''
                line 1 raw
                line 2 raw
                line 3 raw
            ''').strip(),
            expected_status=200,
        ),
        'empty input': SampleDataset(
            fixture_dependency=Dependency(),
            input_value='',
            input_option=True,
            expected_result='empty',
            expected_status=1,
        ),
        'special characters': SampleDataset(
            fixture_dependency=Dependency(),
            input_value='test!@#$%^&*()',
            input_option=True,
            expected_result='test!@#$%^&*() processed',
            expected_status=0,
        ),
    })
    def test_processes_input_correctly(self, dataset: SampleDataset) -> None:
        """Test that input is processed correctly across various cases."""

        # Arrange
        dependency = dataset.fixture_dependency
        processor = SampleProcessor(dependency)

        # Act
        result, status = processor.process(
            dataset.input_value,
            option=dataset.input_option,
        )

        # Assert
        self.assertEqual(result, dataset.expected_result)
        self.assertEqual(status, dataset.expected_status)


class TestValidationError(TestCase):
    """Test validation error handling."""

    @dataclass
    class ErrorDataset:
        fixture_dependency: Dependency
        input_data: Any
        expected_error_type: type[Exception]
        expected_message_contains: str

    @datasets({
        'invalid type': ErrorDataset(
            fixture_dependency=Dependency(),
            input_data=['list', 'not', 'allowed'],
            expected_error_type=TypeError,
            expected_message_contains='must be string',
        ),
        'none value': ErrorDataset(
            fixture_dependency=Dependency(),
            input_data=None,
            expected_error_type=ValueError,
            expected_message_contains='cannot be None',
        ),
        'empty string': ErrorDataset(
            fixture_dependency=Dependency(),
            input_data='',
            expected_error_type=ValueError,
            expected_message_contains='cannot be empty',
        ),
    })
    def test_raises_on_invalid_input(self, dataset: ErrorDataset) -> None:
        """Test that appropriate errors are raised for invalid inputs."""

        # Act & Assert
        with self.assertRaises(dataset.expected_error_type) as context:
            SampleProcessor(dataset.fixture_dependency).process(dataset.input_data)

        self.assertIn(dataset.expected_message_contains, str(context.exception))
```
