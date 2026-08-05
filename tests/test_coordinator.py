"""Tests for the adaptive cover coordinator."""

from __future__ import annotations

import datetime as dt
import types
from unittest.mock import ANY, AsyncMock

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
        self.services = types.SimpleNamespace(async_call=AsyncMock())
        self.config = types.SimpleNamespace(time_zone="UTC")


class FakeStore:
    """Store manual ownership in memory for coordinator tests."""

    def __init__(self, data=None):
        """Initialize stored data."""
        self.data = data

    async def async_load(self):
        """Return stored data."""
        return self.data

    async def async_save(self, data):
        """Record stored data."""
        self.data = data

    def async_delay_save(self, data_func):
        """Record delayed data immediately."""
        self.data = data_func()


def make_coordinator(module, cover_type: SensorType = SensorType.BLIND):
    """Instantiate a coordinator and its surrounding fixtures."""
    hass = HomeAssistant()
    coord = module.SimpleAutoCoverDataUpdateCoordinator.__new__(
        module.SimpleAutoCoverDataUpdateCoordinator
    )
    coord.hass = hass
    coord.config_entry = types.SimpleNamespace(data={}, options={})
    coord._cover_type = cover_type
    coord.min_change = 10
    coord.position_tolerance = 0
    coord.time_threshold = 2
    coord.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None,
        exception=lambda *a, **k: None,
    )
    coord._start_time = None
    coord._end_time = None
    coord.pending_commands = {}
    coord.last_commands = {}
    coord.ignore_intermediate_states = False

    return coord, hass


def make_command(module, target: int, position: int, now: dt.datetime):
    """Create a command record for state-attribution tests."""
    return module.CoverCommand(
        target=target,
        source=module.CommandSource.SOLAR,
        issued_at=now,
        last_progress_at=now,
        last_position=position,
        context_id="command",
    )


def make_manual_manager(module, coord):
    """Create a manual manager without persistence side effects."""
    return module.ManualOverrideManager(
        {"minutes": 15}, coord.logger, lambda _entity_id: None
    )


def enable_manual_detection(module, coord) -> None:
    """Configure a coordinator to detect manual calls for one cover."""
    coord.entities = ["cover.test"]
    coord.manual_toggle = True
    coord.control_toggle = True
    coord.manual_reset = True
    coord.manager = make_manual_manager(module, coord)


def make_cover_service_event(module, context=None):
    """Create a set-position service event for the managed test cover."""
    return module.Event(
        "call_service",
        {
            module.ATTR_DOMAIN: module.COVER_DOMAIN,
            module.ATTR_SERVICE: module.SERVICE_SET_COVER_POSITION,
            module.ATTR_SERVICE_DATA: {module.ATTR_ENTITY_ID: "cover.test"},
        },
        context=context,
    )


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


def test_pos_sun_returns_state_attributes(module):
    """Verify sun attributes are read from the native state API."""
    coord, hass = make_coordinator(module)

    assert coord.pos_sun == [None, None]

    hass.states["sun.sun"] = module.State(
        "sun.sun", "above_horizon", {"azimuth": 180, "elevation": 45}
    )
    assert coord.pos_sun == [180, 45]


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


def test_external_position_bypasses_solar_calibration(module):
    """Use external targets as physical Home Assistant positions."""
    coord, _ = make_coordinator(module)
    coord.external_override = module.ExternalOverride(
        mode=module.OverrideMode.POSITION,
        target=25,
    )

    assert coord.state == 25


@pytest.mark.asyncio
async def test_normal_external_override_respects_manual_control(module):
    """Allow a human manual position to override a normal external target."""
    coord, _ = make_coordinator(module)
    coord.external_override = module.ExternalOverride(
        mode=module.OverrideMode.POSITION,
        target=25,
    )
    coord.manager = types.SimpleNamespace(is_cover_manual=lambda entity: True)
    coord.async_set_position = AsyncMock()

    await coord.async_apply_target("cover.test")

    coord.async_set_position.assert_not_awaited()


@pytest.mark.asyncio
async def test_forced_external_override_bypasses_manual_control(module):
    """Apply an explicitly forced target despite human manual control."""
    coord, _ = make_coordinator(module)
    coord.external_override = module.ExternalOverride(
        mode=module.OverrideMode.POSITION,
        target=25,
        force=True,
    )
    coord.manager = types.SimpleNamespace(is_cover_manual=lambda entity: True)
    coord.async_set_position = AsyncMock()

    await coord.async_apply_target("cover.test")

    coord.async_set_position.assert_awaited_once_with(
        "cover.test",
        25,
        module.CommandSource.FORCED_EXTERNAL_OVERRIDE,
    )


@pytest.mark.asyncio
async def test_manual_state_persists_and_restores_per_cover(module):
    """Persist absolute expiries and restore only active configured covers."""
    coord, _ = make_coordinator(module)
    now = dt.datetime.now(dt.UTC)
    active_expiry = now + dt.timedelta(minutes=30)
    coord._manual_store = FakeStore(
        {
            "cover.active": active_expiry.isoformat(),
            "cover.expired": (now - dt.timedelta(minutes=1)).isoformat(),
            "cover.removed": active_expiry.isoformat(),
        }
    )
    coord.manager = make_manual_manager(module, coord)
    coord.config_entry.options = {
        module.CONF_ENTITIES: ["cover.active", "cover.expired"]
    }

    await coord.async_restore_manual_control()

    assert coord.manager.manual_controlled == ["cover.active"]
    assert coord.manager.expires_at("cover.active") == active_expiry
    assert coord._manual_store.data == {"cover.active": active_expiry.isoformat()}

    await coord.async_save_manual_control()
    assert coord._manual_store.data == {"cover.active": active_expiry.isoformat()}


@pytest.mark.asyncio
async def test_manual_engagement_discards_stale_command_ownership(module):
    """Remove old SAC commands as soon as a cover becomes manual."""
    coord, _ = make_coordinator(module)
    now = dt.datetime.now(dt.UTC)
    command = make_command(module, 50, 10, now)
    coord.pending_commands["cover.test"] = command
    coord.last_commands["cover.test"] = command
    coord._manual_store = FakeStore()
    coord.manager = module.ManualOverrideManager(
        {"minutes": 15}, coord.logger, coord._manual_control_changed
    )

    coord.manager.mark_manual_control("cover.test", False)

    assert "cover.test" not in coord.pending_commands
    assert "cover.test" not in coord.last_commands
    assert coord._manual_store.data == {
        "cover.test": coord.manager.expires_at("cover.test").isoformat()
    }


@pytest.mark.asyncio
async def test_targeted_manual_reset_resumes_only_selected_covers(module):
    """Resume only requested covers whose manual ownership was active."""
    coord, _ = make_coordinator(module)
    coord.entities = ["cover.one", "cover.two"]
    coord.control_toggle = True
    coord.manager = make_manual_manager(module, coord)
    coord.manager.mark_manual_control("cover.one", False)
    coord.manager.mark_manual_control("cover.two", False)
    coord.async_apply_target = AsyncMock()
    coord.async_refresh = AsyncMock()

    await coord.async_reset_manual_overrides({"cover.one"})

    assert coord.manager.is_cover_manual("cover.one") is False
    assert coord.manager.is_cover_manual("cover.two") is True
    coord.async_apply_target.assert_awaited_once_with("cover.one", immediate=True)
    coord.async_refresh.assert_awaited_once()


def test_manual_override_details_include_position_and_expiry(module):
    """Expose each manual cover's physical position and expiry."""
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 65}
    )
    coord.manager = make_manual_manager(module, coord)
    coord.manager.mark_manual_control("cover.test", False)
    started_at = coord.manager.manual_control_time["cover.test"]

    details = coord.manual_override_details["cover.test"]

    assert details["held_position"] == 65
    assert details["started_at"] == started_at.isoformat()
    assert details["expires_at"] == (started_at + dt.timedelta(minutes=15)).isoformat()
    assert 899 <= details["remaining_seconds"] <= 900


def test_control_method_precedence(module):
    """Report disabled, forced, manual, and normal override precedence."""
    coord, _ = make_coordinator(module)
    coord.manager = types.SimpleNamespace(binary_cover_manual=True)
    coord.control_toggle = True
    coord.external_override = module.ExternalOverride(
        mode=module.OverrideMode.POSITION,
        target=25,
    )

    coord._update_control_method()
    assert coord.control_method == "manual"

    coord.external_override = module.ExternalOverride(
        mode=module.OverrideMode.POSITION,
        target=25,
        force=True,
    )
    coord._update_control_method()
    assert coord.control_method == "forced_external_override"

    coord.control_toggle = False
    coord._update_control_method()
    assert coord.control_method == "disabled"


@pytest.mark.asyncio
async def test_hold_override_suppresses_commands(module):
    """Suppress commands while the external override requests a hold."""
    coord, _ = make_coordinator(module)
    coord.external_override = module.ExternalOverride(mode=module.OverrideMode.HOLD)
    coord.async_set_position = AsyncMock()

    await coord.async_apply_target("cover.test")

    coord.async_set_position.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_position_records_pending_and_last_command(module):
    """Record command ownership around a successful service call."""
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 20}
    )

    await coord.async_set_position(
        "cover.test",
        60,
        module.CommandSource.SOLAR,
    )

    command = coord.pending_commands["cover.test"]
    assert command.target == 60
    assert command.source is module.CommandSource.SOLAR
    assert coord.last_commands["cover.test"] is command
    await coord.async_set_position(
        "cover.test",
        60,
        module.CommandSource.SOLAR,
    )
    hass.services.async_call.assert_awaited_once_with(
        module.COVER_DOMAIN,
        module.SERVICE_SET_COVER_POSITION,
        {module.ATTR_ENTITY_ID: "cover.test", module.ATTR_POSITION: 60},
        blocking=True,
        context=ANY,
    )


@pytest.mark.asyncio
async def test_failed_service_call_clears_pending_command(module):
    """Do not attribute later movement to a command that failed to dispatch."""
    coord, hass = make_coordinator(module)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 20}
    )
    hass.services.async_call.side_effect = module.HomeAssistantError("failed")

    await coord.async_set_position(
        "cover.test",
        60,
        module.CommandSource.EXTERNAL_OVERRIDE,
    )

    assert "cover.test" not in coord.pending_commands
    assert "cover.test" not in coord.last_commands


def test_direct_cover_service_call_marks_manual(module):
    """Treat an explicit managed-cover call not sent by SAC as manual."""
    coord, _ = make_coordinator(module)
    enable_manual_detection(module, coord)

    coord.handle_cover_service_call(make_cover_service_event(module))

    assert coord.manager.is_cover_manual("cover.test") is True


@pytest.mark.asyncio
async def test_sac_cover_service_call_is_not_manual(module):
    """Recognize the context assigned to SAC's own service call."""
    coord, hass = make_coordinator(module)
    enable_manual_detection(module, coord)
    hass.states["cover.test"] = module.State(
        "cover.test", "open", {"current_position": 20}
    )
    await coord.async_set_position(
        "cover.test",
        60,
        module.CommandSource.SOLAR,
    )
    context = hass.services.async_call.await_args.kwargs["context"]
    coord.handle_cover_service_call(make_cover_service_event(module, context))

    assert coord.manager.is_cover_manual("cover.test") is False


def test_pending_command_tracks_forward_progress(module):
    """Keep ownership and restart the timeout while moving toward the target."""
    coord, _ = make_coordinator(module)
    now = module.dt_util.utcnow()
    command = make_command(module, 0, 100, now)
    coord.pending_commands["cover.test"] = command
    event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "closing", {"current_position": 100}),
        module.State("cover.test", "closing", {"current_position": 50}),
    )

    assert coord._is_sac_update(event) is True
    assert command.last_position == 50
    assert command.last_progress_at >= now


def test_pending_command_reversal_is_manual(module):
    """Release command ownership as soon as movement reverses direction."""
    coord, _ = make_coordinator(module)
    now = module.dt_util.utcnow()
    coord.pending_commands["cover.test"] = make_command(module, 0, 50, now)
    event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "closing", {"current_position": 50}),
        module.State("cover.test", "opening", {"current_position": 70}),
    )

    assert coord._is_sac_update(event) is False
    assert "cover.test" not in coord.pending_commands


def test_cover_stopping_short_releases_command_ownership(module):
    """Treat a cover that finishes away from its target as manual."""
    coord, _ = make_coordinator(module)
    now = module.dt_util.utcnow()
    coord.pending_commands["cover.test"] = make_command(module, 0, 100, now)
    event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "closing", {"current_position": 100}),
        module.State("cover.test", "open", {"current_position": 50}),
    )

    assert coord._is_sac_update(event) is False
    assert "cover.test" not in coord.pending_commands


def test_position_tolerance_is_independent_of_movement_delta(module):
    """Use only the position-match setting to complete a command."""
    coord, _ = make_coordinator(module)
    now = module.dt_util.utcnow()
    command = make_command(module, 60, 40, now)
    coord.pending_commands["cover.test"] = command
    coord.last_commands["cover.test"] = command
    event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "opening", {"current_position": 40}),
        module.State("cover.test", "opening", {"current_position": 59}),
    )

    assert coord._is_sac_update(event) is True
    assert "cover.test" in coord.pending_commands

    coord.position_tolerance = 1
    assert coord._is_sac_update(event) is True
    assert "cover.test" not in coord.pending_commands

    settled_event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "opening", {"current_position": 59}),
        module.State("cover.test", "open", {"current_position": 59}),
    )
    assert coord._is_sac_update(settled_event) is True


def test_expired_command_no_longer_claims_state_change(module):
    """Allow movement after the no-progress deadline to be considered manual."""
    coord, _ = make_coordinator(module)
    now = module.dt_util.utcnow()
    command = make_command(module, 60, 20, now - dt.timedelta(minutes=1))
    command.last_progress_at = now - module.COMMAND_TRANSIT_TIMEOUT
    coord.pending_commands["cover.test"] = command
    event = module.StateChangedData(
        "cover.test",
        module.State("cover.test", "open", {"current_position": 20}),
        module.State("cover.test", "open", {"current_position": 40}),
    )

    assert coord._is_sac_update(event) is False
    assert "cover.test" not in coord.pending_commands


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
