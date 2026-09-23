# pyright: strict

from dataclasses import dataclass

from sysconf.config.serialization import YamlSerializable
from sysconf.utils.validation import ValidationError, validate, validate_type
from test.datasets import datasets
from test.test_case import TestCase


class TestRequire(TestCase):
    """Test the plain boolean validation helper."""

    @dataclass
    class RequireDataset:
        input_condition: bool
        input_message: str

    @datasets({
        'a true condition': RequireDataset(
            input_condition=True,
            input_message='the file must exist',
        ),
        'a truthy condition': RequireDataset(
            input_condition=bool('non empty'),
            input_message='the file must exist',
        ),
    })
    def test_require_passes_when_the_condition_holds(
        self,
        dataset: RequireDataset,
    ) -> None:
        """Test that a holding condition produces no error and no value."""

        # Act
        result = validate(dataset.input_condition, dataset.input_message)

        # Assert
        self.assertIsNone(result)

    @datasets({
        'a false condition': RequireDataset(
            input_condition=False,
            input_message='the file must exist',
        ),
        'a falsy condition': RequireDataset(
            input_condition=bool(''),
            input_message='the config must not be empty',
        ),
    })
    def test_require_raises_when_the_condition_fails(
        self,
        dataset: RequireDataset,
    ) -> None:
        """Test that a failing condition raises with the given message."""

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            validate(dataset.input_condition, dataset.input_message)

        self.assertEqual(str(context.exception), dataset.input_message)


class TestRequireType(TestCase):
    """Test the type checking validation helper."""

    @dataclass
    class RequireTypeDataset:
        input_value: object
        input_target_type: type[object]
        input_message: str

    @datasets({
        'a string': RequireTypeDataset(
            input_value='echo hello',
            input_target_type=str,
            input_message='must be a string',
        ),
        'an integer': RequireTypeDataset(
            input_value=3,
            input_target_type=int,
            input_message='must be an integer',
        ),
        'a mapping': RequireTypeDataset(
            input_value={'version': '1'},
            input_target_type=dict,
            input_message='must be a mapping',
        ),
        'a sequence': RequireTypeDataset(
            input_value=['echo hello'],
            input_target_type=list,
            input_message='must be a list',
        ),
        'a bool is also an int': RequireTypeDataset(
            input_value=True,
            input_target_type=int,
            input_message='must be an integer',
        ),
    })
    def test_require_type_passes_for_a_matching_type(
        self,
        dataset: RequireTypeDataset,
    ) -> None:
        """Test that a matching type produces no error and returns True."""

        # Act
        result = validate_type(
            dataset.input_value,
            dataset.input_target_type,
            dataset.input_message,
        )

        # Assert
        self.assertTrue(result)

    @datasets({
        'a mapping is not a string': RequireTypeDataset(
            input_value={'script': 'echo hello'},
            input_target_type=str,
            input_message='must be a string',
        ),
        'a sequence is not a mapping': RequireTypeDataset(
            input_value=['echo hello'],
            input_target_type=dict,
            input_message='must be a mapping',
        ),
        'a string is not an integer': RequireTypeDataset(
            input_value='3',
            input_target_type=int,
            input_message='must be an integer',
        ),
        'none is not a mapping': RequireTypeDataset(
            input_value=None,
            input_target_type=dict,
            input_message='must be a mapping',
        ),
    })
    def test_require_type_raises_for_a_mismatched_type(
        self,
        dataset: RequireTypeDataset,
    ) -> None:
        """Test that a mismatched type raises with the given message."""

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            validate_type(
                dataset.input_value,
                dataset.input_target_type,
                dataset.input_message,
            )

        self.assertEqual(str(context.exception), dataset.input_message)

    def test_require_type_narrows_for_the_type_checker(self) -> None:
        """
        Test the `assert require_type(...)` form used at call sites.

        The narrowing itself is enforced by pyright over `test/`: without it,
        the `.keys()` and `.upper()` calls below would not typecheck.
        """

        # Arrange
        data: YamlSerializable = {'version': '1'}

        # Act
        assert validate_type(data, dict, 'must be a mapping')
        version = data['version']
        assert validate_type(version, str, 'version must be a string')

        # Assert
        self.assertEqual(list(data.keys()), ['version'])
        self.assertEqual(version.upper(), '1')
