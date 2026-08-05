"""Tests for ManualOverrideManager."""

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
    """Create a ManualOverrideManager instance for testing."""

    logger = types.SimpleNamespace(debug=lambda *a, **k: None)
    return manager_module.ManualOverrideManager(
        {"seconds": seconds}, logger, lambda _entity_id: None
    )


def make_state(entity_id: str, position: int, cover_type: str | SensorType = "cover"):
    """Return a `State` object with the desired position."""

    from homeassistant.core import State

    attr = {
        "current_tilt_position"
        if cover_type == SensorType.TILT or cover_type == "cover_tilt"
        else "current_position": position
    }
    return State(entity_id, "open", attr, last_updated=dt.datetime.now(dt.UTC))


def test_manual_state_change_callback_and_restore(manager_module):
    """Notify persistence hooks and restore an absolute expiry."""
    changes = []
    logger = types.SimpleNamespace(debug=lambda *a, **k: None)
    manager = manager_module.ManualOverrideManager(
        {"minutes": 15}, logger, changes.append
    )
    now = dt.datetime.now(dt.UTC)

    manager.mark_manual_control("cover.one", False)
    manager.mark_manual_control("cover.one", False)
    manager.reset("cover.one")

    assert changes == ["cover.one", "cover.one"]

    expires_at = now + dt.timedelta(hours=1)
    manager.restore("cover.two", expires_at)
    assert manager.is_cover_manual("cover.two")
    assert manager.expires_at("cover.two") == expires_at
    assert changes == ["cover.one", "cover.one"]


def test_add_and_basic_properties(manager_module):
    """Verify that covers are added and tracked correctly."""
    manager = make_manager(manager_module)
    manager.mark_manual_control("cover.one", False)
    assert manager.is_cover_manual("cover.one") is True
    assert manager.binary_cover_manual is True
    assert manager.manual_controlled == ["cover.one"]


def test_handle_state_change_marks_manual(manager_module, state_data_class):
    """Ensure state changes mark covers as manual when appropriate."""
    manager = make_manager(manager_module)
    our_state = 10
    event = state_data_class(
        "cover.test",
        make_state("cover.test", 10),
        make_state("cover.test", 50),
    )
    manager.handle_state_change(event, our_state, SensorType.BLIND, True, None)
    assert manager.is_cover_manual("cover.test") is True
    assert "cover.test" in manager.manual_control_time


def test_unchanged_position_is_not_manual(manager_module, state_data_class):
    """Ignore state transitions that do not change the reported position."""
    manager = make_manager(manager_module)
    event = state_data_class(
        "cover.test",
        make_state("cover.test", 50),
        make_state("cover.test", 50),
    )

    manager.handle_state_change(event, 10, SensorType.BLIND, True, None)

    assert manager.is_cover_manual("cover.test") is False


def test_final_state_detects_ignored_intermediate_movement(
    manager_module, state_data_class
):
    """Detect a completed movement after intermediate states were ignored."""
    manager = make_manager(manager_module)
    old_state = make_state("cover.test", 50)
    old_state.state = "opening"
    event = state_data_class(
        "cover.test",
        old_state,
        make_state("cover.test", 50),
    )

    manager.handle_state_change(event, 10, SensorType.BLIND, True, None)

    assert manager.is_cover_manual("cover.test") is True


def test_handle_state_change_threshold(manager_module, state_data_class):
    """Check manual control is not set when below threshold."""
    manager = make_manager(manager_module)
    our_state = 10
    event = state_data_class(
        "cover.test",
        make_state("cover.test", 10),
        make_state("cover.test", 12),
    )
    manager.handle_state_change(event, our_state, SensorType.BLIND, True, 5)
    assert manager.is_cover_manual("cover.test") is False


def test_reset_if_needed(manager_module, state_data_class):
    """Validate that manual control flags reset after the cooldown."""
    manager = make_manager(manager_module, seconds=0)
    past_state = make_state("cover.test", 50)
    past_state.last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    event = state_data_class(
        "cover.test",
        make_state("cover.test", 10),
        past_state,
    )
    manager.handle_state_change(event, 10, SensorType.BLIND, True, None)
    assert manager.is_cover_manual("cover.test")
    assert manager.reset_if_needed() == ["cover.test"]
    assert manager.is_cover_manual("cover.test") is False
