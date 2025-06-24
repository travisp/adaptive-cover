"""Tests for AdaptiveCoverManager."""

from __future__ import annotations

import datetime as dt
import types

import pytest

from custom_components.simple_auto_cover.const import SensorType


@pytest.fixture
def manager_module():
    """Import and return the cover_manager module under test."""

    import custom_components.simple_auto_cover.cover_manager as manager

    return manager


@pytest.fixture
def state_data_class(coordinator):
    """Return the data class used for state change events."""

    return coordinator.StateChangedData


def make_manager(manager_module, seconds=30):
    """Create an AdaptiveCoverManager instance for testing."""

    logger = types.SimpleNamespace(debug=lambda *a, **k: None)
    return manager_module.AdaptiveCoverManager({"seconds": seconds}, logger)


def make_state(entity_id: str, position: int, cover_type: str | SensorType = "cover"):
    """Return a `State` object with the desired position."""

    from homeassistant.core import State

    attr = {
        "current_tilt_position"
        if cover_type == SensorType.TILT or cover_type == "cover_tilt"
        else "current_position": position
    }
    return State(entity_id, "open", attr, last_updated=dt.datetime.now(dt.UTC))


def test_add_and_basic_properties(manager_module):
    """Verify that covers are added and tracked correctly."""
    manager = make_manager(manager_module)
    manager.add_covers({"cover.one", "cover.two"})
    assert manager.covers == {"cover.one", "cover.two"}
    manager.mark_manual_control("cover.one")
    assert manager.is_cover_manual("cover.one") is True
    assert manager.binary_cover_manual is True
    assert manager.manual_controlled == ["cover.one"]


def test_handle_state_change_marks_manual(manager_module, state_data_class):
    """Ensure state changes mark covers as manual when appropriate."""
    manager = make_manager(manager_module)
    manager.add_covers({"cover.test"})
    our_state = 10
    event = state_data_class("cover.test", None, make_state("cover.test", 50))
    manager.handle_state_change(event, our_state, SensorType.BLIND, True, {}, None)
    assert manager.is_cover_manual("cover.test") is True
    assert "cover.test" in manager.manual_control_time


def test_handle_state_change_threshold(manager_module, state_data_class):
    """Check manual control is not set when below threshold."""
    manager = make_manager(manager_module)
    manager.add_covers({"cover.test"})
    our_state = 10
    event = state_data_class("cover.test", None, make_state("cover.test", 12))
    manager.handle_state_change(event, our_state, SensorType.BLIND, True, {}, 5)
    assert manager.is_cover_manual("cover.test") is False


def test_reset_if_needed(manager_module, state_data_class):
    """Validate that manual control flags reset after the cooldown."""
    manager = make_manager(manager_module, seconds=0)
    manager.add_covers({"cover.test"})
    past_state = make_state("cover.test", 50)
    past_state.last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    event = state_data_class("cover.test", None, past_state)
    manager.handle_state_change(event, 10, SensorType.BLIND, True, {}, None)
    assert manager.is_cover_manual("cover.test")
    import asyncio

    asyncio.run(manager.reset_if_needed())
    assert manager.is_cover_manual("cover.test") is False
