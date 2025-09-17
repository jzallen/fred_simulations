"""Pytest configuration for TCR tests."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_logger_for_tests():
    """Disable logger initialization during tests to avoid creating log files."""
    os.environ['IS_TCR_LOGGER_ENABLED'] = 'false'
    yield
    # Clean up after tests
    os.environ.pop('IS_TCR_LOGGER_ENABLED', None)