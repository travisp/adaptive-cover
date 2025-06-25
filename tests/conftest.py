"""Fixtures and helper utilities for the test suite."""

import pytest


@pytest.fixture
def calculation():
    """Provide the calculation module used in tests."""
    import custom_components.simple_auto_cover.calculation as calculation

    return calculation


@pytest.fixture
def coordinator():
    """Provide the coordinator module used in tests."""
    import custom_components.simple_auto_cover.coordinator as coordinator

    return coordinator
