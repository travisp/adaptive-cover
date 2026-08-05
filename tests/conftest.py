"""Fixtures and helper utilities for the test suite."""

import asyncio

import pytest


@pytest.fixture(autouse=True)
def enable_event_loop_debug() -> None:
    """Ensure the Home Assistant test plugin always has a current event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.set_debug(True)


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
