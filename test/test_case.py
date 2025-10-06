# pyright: strict

from unittest import TestCase as _TestCase


class TestCase(_TestCase):
    """
    Project wide base test case class, this should be used instead of 
    unittest.TestCase
    """

    maxDiff = None
