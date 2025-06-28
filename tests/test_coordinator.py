"""Tests for the adaptive cover coordinator."""

from __future__ import annotations

import datetime as dt
import types
import pytest

from custom_components.simple_auto_cover.const import SensorType


@pytest.fixture
def module(coordinator):
    """Return the coordinator module under test."""
    return coordinator


class DummyStates(dict):
    """Minimal stand-in for :class:`homeassistant.core.States`."""

    def get(self, entity_id):
        """Return the entity state if present."""
        return super().get(entity_id)


class HomeAssistant:
    """Simplified Home Assistant instance for tests."""

    def __init__(self, config_dir: str = "/tmp") -> None:
        """Initialize the dummy instance."""
        self.states = DummyStates()
        self.services = types.SimpleNamespace(async_call=lambda *a, **kw: None)
        self.config = types.SimpleNamespace(time_zone="UTC")


def make_coordinator(module, cover_type: SensorType = SensorType.BLIND):
    """Instantiate a coordinator and its surrounding fixtures."""
    hass = HomeAssistant()
    coord = module.AdaptiveDataUpdateCoordinator.__new__(
        module.AdaptiveDataUpdateCoordinator
    )
    coord.hass = hass
    coord.config_entry = types.SimpleNamespace(data={}, options={})
    coord._cover_type = cover_type
    coord.min_change = 10
    coord.time_threshold = 2
    coord.logger = types.SimpleNamespace(debug=lambda *a, **k: None)
    coord._start_time = None
    coord._end_time = None

    return coord, hass


def test_get_current_position(module):
    """Verify that the current position is read correctly."""
    coord, hass = make_coordinator(module, SensorType.BLIND)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 40}
    )
    assert coord._get_current_position("cover.test") == 40

    coord._cover_type = SensorType.TILT
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_tilt_position": 30}
    )
    assert coord._get_current_position("cover.test") == 30


def test_check_position(module):
    """Ensure the coordinator detects position changes."""
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 40}
    )
    assert coord.check_position("cover.test", 50) is True
    assert coord.check_position("cover.test", 40) is False

    hass.states.pop("cover.test")
    assert coord.check_position("cover.test", 30) is False


def test_check_position_delta(module):
    """Check that large enough deltas trigger updates."""
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 40}
    )
    options = {module.CONF_SUNSET_POS: 0, module.CONF_DEFAULT_HEIGHT: 50}

    assert coord.check_position_delta("cover.test", 45, options) is False
    assert coord.check_position_delta("cover.test", 55, options) is True
    assert coord.check_position_delta("cover.test", 0, options) is True

    hass.states.pop("cover.test")
    assert coord.check_position_delta("cover.test", 30, options) is True


def test_check_time_delta(module):
    """Check that updates occur after the time threshold."""
    coord, hass = make_coordinator(module)
    past = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=3)
    hass.states["cover.test"] = module.State("cover.test", "open", last_updated=past)
    assert coord.check_time_delta("cover.test") is True

    hass.states["cover.test"].last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(
        minutes=1
    )
    assert coord.check_time_delta("cover.test") is False

    hass.states.pop("cover.test")
    assert coord.check_time_delta("cover.test") is True


def test_inverse_state(module):
    """Test inversion utility for tilt covers."""
    assert module.inverse_state(20) == 80


def test_async_timed_refresh_without_end_time(module):
    """Execute ``async_timed_refresh`` when no end time is set."""
    coord, hass = make_coordinator(module)
    coord.end_time = None
    coord.end_time_entity = None
    coord.timed_refresh = False
    import asyncio

    asyncio.run(coord.async_timed_refresh(None))
    assert coord.timed_refresh is False


def test_update_datetime_objects_sets_times(module):
    """Ensure time strings are parsed and stored."""
    coord, hass = make_coordinator(module)
    coord.start_time = "08:00"
    coord.end_time = "17:00"
    coord.start_time_entity = None
    coord.end_time_entity = None
    coord._update_datetime_objects()
    assert coord._start_time is not None
    assert coord._end_time is not None


def test_update_datetime_objects_midnight_rollover(module, monkeypatch):
    """Ensure midnight end time rolls over to the next day."""

    coord, _ = make_coordinator(module)

    def fake_get_datetime(value):
        return dt.datetime(2022, 1, 1, 0, 0)

    monkeypatch.setattr(module, "get_datetime_from_str", fake_get_datetime)

    coord.start_time = None
    coord.end_time = "00:00"
    coord.start_time_entity = None
    coord.end_time_entity = None

    coord._update_datetime_objects()

    assert coord._end_time == dt.datetime(2022, 1, 2, 0, 0)


def test_interpolate_states_default(module):
    """Ensure no adjustment occurs with no custom range."""
    coord, _ = make_coordinator(module)
    coord.start_value = None
    coord.end_value = None
    coord.normal_list = []
    coord.new_list = []
    assert coord.interpolate_states(50) == 50


def test_interpolate_states_start_only(module):
    """Interpolate when only the starting value is provided."""
    coord, _ = make_coordinator(module)
    coord.start_value = 20
    coord.end_value = None
    coord.normal_list = []
    coord.new_list = []
    assert coord.interpolate_states(50) == 60


def test_interpolate_states_end_only(module):
    """Interpolate when only the ending value is provided."""
    coord, _ = make_coordinator(module)
    coord.start_value = None
    coord.end_value = 80
    coord.normal_list = []
    coord.new_list = []
    assert coord.interpolate_states(50) == 40


def test_interpolate_states_full_range(module):
    """Interpolate when both start and end values are provided."""
    coord, _ = make_coordinator(module)
    coord.start_value = 10
    coord.end_value = 90
    coord.normal_list = []
    coord.new_list = []
    assert coord.interpolate_states(50) == 50


def test_vertical_data_force_no_sunny_area(module):
    """Distance is set to zero when forcing no sunny area."""
    from custom_components.simple_auto_cover.const import CONF_DISTANCE, CONF_HEIGHT_WIN, FORCE_NO_SUNNY_AREA

    coord, _ = make_coordinator(module)
    coord.force_mode = FORCE_NO_SUNNY_AREA
    options = {CONF_DISTANCE: 0.5, CONF_HEIGHT_WIN: 2.0}
    config = module.CoverConfig()
    coord.vertical_data(options, config)

    assert config.distance == 0
