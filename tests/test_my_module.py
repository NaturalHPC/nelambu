"""Tests for the nelambu.my_module module."""

import pytest
from nelambu import hello


def test_hello() -> None:
    """Example using assert."""
    assert hello("nlesc") == "Hello nlesc!"


def test_hello_with_error() -> None:
    """Example of testing for raised errors."""
    with pytest.raises(ValueError) as excinfo:
        hello("nobody")
    assert "Can not say hello to nobody" in str(excinfo.value)


@pytest.fixture
def some_name() -> None:
    """Example fixture."""
    return "Jane Smith"


def test_hello_with_fixture(some_name: str) -> None:
    """Example using a fixture."""
    assert hello(some_name) == "Hello Jane Smith!"
