# pyright: strict

from functools import wraps
from typing import Callable, TypeVar
from unittest import TestCase

D = TypeVar('D')
S = TypeVar('S', bound=TestCase)


def datasets(
    datasets: dict[str, D],
    setUpDataset: Callable[[S, D], None] = lambda self, dataset: None,
    tearDownDataset: Callable[[S, D], None] = lambda self, dataset: None
) -> Callable[[Callable[[S, D], None]], Callable[[S], None]]:
    """
    A decorator factory that allows running a test method with multiple datasets.
    It uses the `subTest` context manager to create subtests for each dataset,
    and runs the `test_method` for each dataset.

    Args:
        datasets (dict[str, T]): A dictionary containing the datasets to be used for testing.
        setUpDataset (Callable): A method to be called before running the test method for each dataset.
        tearDownDataset (Callable): A method to be called after running the test method for each dataset.

    Returns:
        Callable: The decorated test method.

    Example:
        @datasets({'dataset1': [1, 2, 3], 'dataset2': [4, 5, 6]})
        def test_method(self, dataset: list[int]):
            # Test implementation
    """

    def decorator(test_method: Callable[[S, D], None]) -> Callable[[S], None]:
        """
        A decorator function that wraps a test method and runs it for each dataset in the 'datasets' dictionary.

        Args:
            test_method (Callable): The test method to be wrapped.

        Returns:
            Callable: The wrapped test method.

        """

        @wraps(test_method)
        def wrapper_test(self: S) -> None:
            """
            A wrapper method for testing datasets.

            This method iterates over the datasets and runs the `test_method` for each dataset.
            It uses the `subTest` context manager to create subtests for each dataset.

            Parameters:
            - self: The instance of the test class.

            Returns:
            - None
            """

            for name, dataset in datasets.items():
                with self.subTest(name=name):
                    setUpDataset(self, dataset)
                    try:
                        test_method(self, dataset)
                    finally:
                        tearDownDataset(self, dataset)

        return wrapper_test

    return decorator
