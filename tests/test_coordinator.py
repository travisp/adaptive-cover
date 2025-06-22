"""Tests for the adaptive cover coordinator."""

from __future__ import annotations

import datetime as dt
import types
import pytest


@pytest.fixture
def module(coordinator):
    return coordinator


class DummyStates(dict):
    def get(self, entity_id):
        return super().get(entity_id)


class HomeAssistant:
    def __init__(self, config_dir: str = "/tmp") -> None:
        self.states = DummyStates()
        self.services = types.SimpleNamespace(async_call=lambda *a, **kw: None)
        self.config = types.SimpleNamespace(time_zone="UTC")


def make_coordinator(module, cover_type="cover_blind"):
    hass = HomeAssistant()
    coord = module.AdaptiveDataUpdateCoordinator.__new__(module.AdaptiveDataUpdateCoordinator)
    coord.hass = hass
    coord.config_entry = types.SimpleNamespace(data={}, options={})
    coord._cover_type = cover_type
    coord.min_change = 10
    coord.time_threshold = 2
    coord.logger = types.SimpleNamespace(debug=lambda *a, **k: None)

    return coord, hass


def test_get_current_position(module):
    coord, hass = make_coordinator(module, "cover_blind")
    hass.states["cover.test"] = module.State("cover.test", "open", {"current_position": 40})
    assert coord._get_current_position("cover.test") == 40

    coord._cover_type = "cover_tilt"
    hass.states["cover.test"] = module.State("cover.test", "open", {"current_tilt_position": 30})
    assert coord._get_current_position("cover.test") == 30


def test_check_position(module):
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State("cover.test", "open", {"current_position": 40})
    assert coord.check_position("cover.test", 50) is True
    assert coord.check_position("cover.test", 40) is False

    hass.states.pop("cover.test")
    assert coord.check_position("cover.test", 30) is False


def test_check_position_delta(module):
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State("cover.test", "open", {"current_position": 40})
    options = {module.CONF_SUNSET_POS: 0, module.CONF_DEFAULT_HEIGHT: 50}

    assert coord.check_position_delta("cover.test", 45, options) is False
    assert coord.check_position_delta("cover.test", 55, options) is True
    assert coord.check_position_delta("cover.test", 0, options) is True

    hass.states.pop("cover.test")
    assert coord.check_position_delta("cover.test", 30, options) is True


def test_check_time_delta(module):
    coord, hass = make_coordinator(module)
    past = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=3)
    hass.states["cover.test"] = module.State("cover.test", "open", last_updated=past)
    assert coord.check_time_delta("cover.test") is True

    hass.states["cover.test"].last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1)
    assert coord.check_time_delta("cover.test") is False

    hass.states.pop("cover.test")
    assert coord.check_time_delta("cover.test") is True


def test_inverse_state(module):
    assert module.inverse_state(20) == 80


def test_async_timed_refresh_without_end_time(module):
    coord, hass = make_coordinator(module)
    coord.end_time = None
    coord.end_time_entity = None
    coord.timed_refresh = False
    import asyncio

    asyncio.run(coord.async_timed_refresh(None))
    assert coord.timed_refresh is False
