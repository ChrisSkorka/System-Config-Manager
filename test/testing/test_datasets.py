# pyright: strict

from typing import Callable, Self
from unittest import mock

from test.datasets import datasets
from test.test_case import TestCase


class DatasetTest(TestCase):

    def test_datasets_callable(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}

        # Act
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        # Assert
        self.assertTrue(callable(decorator))

    def test_decorator(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        def test_method(self: Self, dataset: list[int]):
            pass

        # Act
        wrapped_test_method = decorator(test_method)

        # Assert
        self.assertTrue(callable(wrapped_test_method))

    def test_call_count(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        mock_test_method = mock.MagicMock()
        wrapped_test_method = decorator(mock_test_method)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            wrapped_test_method(self)

        # Assert
        self.assertEqual(mock_test_method.call_count, 2)
        self.assertEqual(mock_subtest.call_count, 2)

    def test_test_name(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        mock_test_method = mock.MagicMock()
        wrapped_test_method = decorator(mock_test_method)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            wrapped_test_method(self)

        # Assert
        mock_subtest.assert_any_call(name='dataset1')
        mock_subtest.assert_any_call(name='dataset2')

    def test_test_parameter(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        mock_test_method = mock.MagicMock()
        wrapped_test_method = decorator(mock_test_method)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            wrapped_test_method(self)

        # Assert
        mock_subtest.assert_any_call(name='dataset1')
        mock_subtest.assert_any_call(name='dataset2')
        mock_test_method.assert_has_calls([
            mock.call(self, [1, 2, 3]),
            mock.call(self, [4, 5, 6]),
        ])

    def test_failed_dataset_test(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        def test_method(self: Self, dataset: list[int]):
            self.assertTrue(False)

        wrapped_test_method = decorator(test_method)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            with self.assertRaises(AssertionError):
                wrapped_test_method(self)

        # Assert
        # subTest is mocked so that it does not correctly log the test failure,
        # but because of this it also does not recover from the exceptions and
        # the second dataset is not run.
        self.assertEqual(mock_subtest.call_count, 1)

    def test_error_dataset_test(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(data)

        def test_method(self: Self, dataset: list[int]):
            raise ValueError('test')

        wrapped_test_method = decorator(test_method)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            with self.assertRaises(ValueError):
                wrapped_test_method(self)

        # Assert
        # subTest is mocked so that it does not correctly log the test failure,
        # but because of this it also does not recover from the exceptions and
        # the second dataset is not run.
        self.assertEqual(mock_subtest.call_count, 1)

    def test_setup_teardown_dataset(self):
        # Arrange
        data = {'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]}
        calls: list[tuple[str, Self, list[int]]] = []

        def setUpDataset(self: Self, dataset: list[int]):
            calls.append(('setUpDataset', self, dataset))

        def tearDownDataset(self: Self, dataset: list[int]):
            calls.append(('tearDownDataset', self, dataset))

        def testMethod(self: Self, dataset: list[int]):
            calls.append(('testMethod', self, dataset))

        decorator: Callable[
            [Callable[[Self, list[int]], None]],
            Callable[[Self], None]
        ] = datasets(
            data,
            setUpDataset=setUpDataset,
            tearDownDataset=tearDownDataset,
        )
        wrapped_test_method = decorator(testMethod)

        # Act
        with mock.patch.object(self, 'subTest') as mock_subtest:
            wrapped_test_method(self)

        # Assert
        mock_subtest.assert_any_call(name='dataset1')
        mock_subtest.assert_any_call(name='dataset2')
        self.assertEqual(
            calls,
            [
                ('setUpDataset', self, [1, 2, 3]),
                ('testMethod', self, [1, 2, 3]),
                ('tearDownDataset', self, [1, 2, 3]),
                ('setUpDataset', self, [4, 5, 6]),
                ('testMethod', self, [4, 5, 6]),
                ('tearDownDataset', self, [4, 5, 6]),
            ],
        )
