"""Fixtures for Delayed Tasks integration tests."""
from collections.abc import Generator
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None, None, None]:
    """Enable custom integrations in Home Assistant."""
    yield
