"""Tests for AdaptiveCoverManager."""

from __future__ import annotations

import datetime as dt
import types

import pytest


@pytest.fixture
def manager_module():
    from tests.conftest import import_module

    return import_module(
        "custom_components/simple_auto_cover/cover_manager.py",
        "custom_components.simple_auto_cover.cover_manager",
    )


@pytest.fixture
def state_data_class(coordinator):
    return coordinator.StateChangedData


def make_manager(manager_module, seconds=30):
    logger = types.SimpleNamespace(debug=lambda *a, **k: None)
    return manager_module.AdaptiveCoverManager({"seconds": seconds}, logger)


def make_state(entity_id: str, position: int, cover_type="cover"):
    from homeassistant.core import State

    attr = {
        "current_tilt_position"
        if cover_type == "cover_tilt"
        else "current_position": position
    }
    return State(entity_id, "open", attr, last_updated=dt.datetime.now(dt.UTC))


def test_add_and_basic_properties(manager_module):
    manager = make_manager(manager_module)
    manager.add_covers({"cover.one", "cover.two"})
    assert manager.covers == {"cover.one", "cover.two"}
    manager.mark_manual_control("cover.one")
    assert manager.is_cover_manual("cover.one") is True
    assert manager.binary_cover_manual is True
    assert manager.manual_controlled == ["cover.one"]


def test_handle_state_change_marks_manual(manager_module, state_data_class):
    manager = make_manager(manager_module)
    manager.add_covers({"cover.test"})
    our_state = 10
    event = state_data_class("cover.test", None, make_state("cover.test", 50))
    manager.handle_state_change(event, our_state, "cover", True, {}, None)
    assert manager.is_cover_manual("cover.test") is True
    assert "cover.test" in manager.manual_control_time


def test_handle_state_change_threshold(manager_module, state_data_class):
    manager = make_manager(manager_module)
    manager.add_covers({"cover.test"})
    our_state = 10
    event = state_data_class("cover.test", None, make_state("cover.test", 12))
    manager.handle_state_change(event, our_state, "cover", True, {}, 5)
    assert manager.is_cover_manual("cover.test") is False


def test_reset_if_needed(manager_module, state_data_class):
    manager = make_manager(manager_module, seconds=0)
    manager.add_covers({"cover.test"})
    past_state = make_state("cover.test", 50)
    past_state.last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    event = state_data_class("cover.test", None, past_state)
    manager.handle_state_change(event, 10, "cover", True, {}, None)
    assert manager.is_cover_manual("cover.test")
    import asyncio

    asyncio.run(manager.reset_if_needed())
    assert manager.is_cover_manual("cover.test") is False
