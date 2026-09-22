# pyright: strict

from dataclasses import dataclass
from sysconf.utils.str import unindent
from test.datasets import datasets
from test.test_case import TestCase


class TestUnindent(TestCase):

    @dataclass
    class Dataset:
        input: str
        expected: str

    @datasets({
        'basic usage from docstring': Dataset(
            input="""
                line 1
                    line 2
                line 3
            """,
            expected="line 1\n    line 2\nline 3",
        ),
        'single line': Dataset(
            input="""
                single
            """,
            expected="single",
        ),
        'uniform indentation removed': Dataset(
            input="""
                line 1
                line 2
            """,
            expected="line 1\nline 2",
        ),
        'empty lines in the middle are preserved': Dataset(
            input="""
                line 1

                line 3
            """,
            expected="line 1\n\nline 3",
        ),
        'deeper common indentation is fully removed': Dataset(
            input="""
                    deeper
                        even deeper
                    back
            """,
            expected="deeper\n    even deeper\nback",
        ),
        'trailing whitespace on lines preserved': Dataset(
            input="""
                line 1
                line 2
            """,
            expected="line 1\nline 2",
        ),
    })
    def test_unindent(self, dataset: Dataset) -> None:
        # Act
        result = unindent(dataset.input)

        # Assert
        self.assertEqual(result, dataset.expected)
