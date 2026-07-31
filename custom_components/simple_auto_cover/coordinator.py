"""The Coordinator for Simple Auto Cover."""

from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from homeassistant.util import dt as dt_util
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    CONF_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_STOP_COVER_TILT,
)
from homeassistant.core import (
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_context_adapter import ConfigContextAdapter

from .calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    NormalCoverState,
    CoverConfig,
)
from .const import (
    _LOGGER,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_LIST,
    CONF_INTERP_LIST_NEW,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_OVERRIDE_ENTITY,
    CONF_POSITION_TOLERANCE,
    CONF_RETURN_SUNSET,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_SENSOR_TYPE,
    DOMAIN,
    LOGGER,
    SensorType,
)
from .helpers import get_datetime_from_str, get_last_updated, get_safe_state
from .cover_manager import ManualOverrideManager
from .override import ExternalOverride, OverrideMode, parse_external_override


COMMAND_TRANSIT_TIMEOUT = dt.timedelta(seconds=45)
MANUAL_OVERRIDE_STORAGE_VERSION = 1
MANUAL_COVER_SERVICES = {
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_STOP_COVER_TILT,
}


class CommandSource(StrEnum):
    """Reasons Simple Auto Cover sends a cover command."""

    SOLAR = "solar"
    EXTERNAL_OVERRIDE = "external_override"
    FORCED_EXTERNAL_OVERRIDE = "forced_external_override"
    TIMED_END = "timed_end"


@dataclass
class CoverCommand:
    """A command and the latest progress reported by its cover."""

    target: int
    source: CommandSource
    issued_at: dt.datetime
    last_progress_at: dt.datetime
    last_position: int
    context_id: str

    @property
    def expires_at(self) -> dt.datetime:
        """Return when command ownership expires without more progress."""
        return self.last_progress_at + COMMAND_TRANSIT_TIMEOUT


@dataclass
class StateChangedData:
    """States before and after a managed cover update."""

    entity_id: str
    old_state: State
    new_state: State


@dataclass
class AdaptiveCoverData:
    """State and attributes exposed by Simple Auto Cover entities."""

    states: dict
    attributes: dict


class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        super().__init__(hass, LOGGER, name=DOMAIN)

        self.logger = ConfigContextAdapter(_LOGGER)
        self.logger.set_config_name(self.config_entry.data.get(CONF_NAME))
        self._cover_type = self.config_entry.data.get(CONF_SENSOR_TYPE)
        self._inverse_state = self.config_entry.options.get(CONF_INVERSE_STATE, False)
        self._use_interpolation = self.config_entry.options.get(CONF_INTERP, False)
        self._track_end_time = self.config_entry.options.get(CONF_RETURN_SUNSET)
        self._control_toggle = None
        self._manual_toggle = None
        self._start_time = None
        self._sun_end_time = None
        self._sun_start_time = None
        self._end_time: dt.datetime | None = None
        self.override_entity: str | None = None
        self.external_override = ExternalOverride(mode=OverrideMode.AUTO)
        self.manual_reset = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_RESET, False
        )
        manual_duration = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15}
        )
        self.state_change = False
        self.timed_refresh = False
        self.control_method = "solar"
        self.manager = ManualOverrideManager(
            manual_duration,
            self.logger,
            self._manual_control_changed,
        )
        self.pending_commands: dict[str, CoverCommand] = {}
        self.last_commands: dict[str, CoverCommand] = {}
        self._manual_store = Store(
            hass,
            MANUAL_OVERRIDE_STORAGE_VERSION,
            f"{DOMAIN}.manual_override.{self.config_entry.entry_id}",
        )
        self.ignore_intermediate_states = self.config_entry.options.get(
            CONF_MANUAL_IGNORE_INTERMEDIATE, False
        )
        self._update_listener = None
        self._scheduled_time = dt.datetime.now()

    @callback
    def _manual_control_changed(self, entity_id: str) -> None:
        """Persist manual state and discard stale command ownership."""
        if self.manager.is_cover_manual(entity_id):
            self.pending_commands.pop(entity_id, None)
            self.last_commands.pop(entity_id, None)
        self._manual_store.async_delay_save(self._manual_storage_data)

    def _manual_storage_data(self) -> dict[str, str]:
        """Return persisted manual expiry data."""
        return {
            entity_id: self.manager.expires_at(entity_id).isoformat()
            for entity_id in self.manager.manual_controlled
        }

    async def async_save_manual_control(self) -> None:
        """Persist the absolute expiry of each manual cover."""
        await self._manual_store.async_save(self._manual_storage_data())

    async def async_restore_manual_control(self) -> None:
        """Restore unexpired manual ownership before the first refresh."""
        managed_covers = set(self.config_entry.options.get(CONF_ENTITIES, []))
        stored = await self._manual_store.async_load() or {}
        now = dt_util.utcnow()
        for entity_id, expires_at_value in stored.items():
            expires_at = dt.datetime.fromisoformat(expires_at_value)
            if entity_id in managed_covers and expires_at > now:
                self.manager.restore(entity_id, expires_at)

        if stored != self._manual_storage_data():
            await self.async_save_manual_control()

    async def async_timed_refresh(self, _event) -> None:
        """Control state at end time."""

        now = dt.datetime.now()
        time = None
        if self.end_time is not None:
            time = self.end_time
        if self.end_time_entity is not None:
            time = get_safe_state(self.hass, self.end_time_entity)

        self.logger.debug("Checking timed refresh. End time: %s, now: %s", time, now)
        if time is None:
            self.logger.debug("Timed refresh aborted: no end time configured")
            return

        time_check = now - get_datetime_from_str(time)
        if time_check <= dt.timedelta(seconds=1):
            self.timed_refresh = True
            self.logger.debug("Timed refresh triggered")
            await self.async_refresh()
        else:
            self.logger.debug("Timed refresh, but: not equal to end time")

    async def async_check_entity_state_change(
        self, _event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Entity state change")
        self.state_change = True
        await self.async_refresh()

    @callback
    def handle_cover_service_call(self, event: Event) -> None:
        """Treat direct cover service calls not sent by SAC as manual control."""
        if (
            event.data.get(ATTR_DOMAIN) != COVER_DOMAIN
            or event.data.get(ATTR_SERVICE) not in MANUAL_COVER_SERVICES
        ):
            return

        context_id = event.context.id
        if any(
            command.context_id == context_id
            for command in self.pending_commands.values()
        ) or any(
            command.context_id == context_id for command in self.last_commands.values()
        ):
            return
        if not self.manual_toggle or not self.control_toggle:
            return

        targeted_entities = event.data[ATTR_SERVICE_DATA].get(ATTR_ENTITY_ID)
        if targeted_entities is None:
            return
        if isinstance(targeted_entities, str):
            targeted_entities = [targeted_entities]

        for entity_id in set(targeted_entities).intersection(self.entities):
            self.manager.mark_manual_control(entity_id, self.manual_reset)
            self.logger.debug("Manual cover service call detected for %s", entity_id)

    async def async_check_cover_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Cover state change")
        data = event.data
        old_state = data["old_state"]
        new_state = data["new_state"]
        if old_state is None or new_state is None:
            return
        if old_state.state in ["unknown", "unavailable"] or new_state.state in [
            "unknown",
            "unavailable",
        ]:
            return

        state_change = StateChangedData(data["entity_id"], old_state, new_state)
        expected_update = self._is_sac_update(state_change)

        if self.manual_toggle and self.control_toggle and not expected_update:
            self.manager.handle_state_change(
                state_change,
                self.state,
                self._cover_type,
                self.manual_reset,
                self.manual_threshold,
            )

        if self.control_toggle and self.external_override.force and not expected_update:
            await self.async_set_position(
                state_change.entity_id,
                self.external_override.target,
                CommandSource.FORCED_EXTERNAL_OVERRIDE,
            )

        await self.async_refresh()

    def _is_sac_update(self, event: StateChangedData) -> bool:
        """Return whether a state change belongs to an active SAC command."""
        self.logger.debug("Processing state change event: %s", event)
        entity_id = event.entity_id
        position_attribute = (
            "current_tilt_position"
            if self._cover_type == SensorType.TILT
            else "current_position"
        )
        position = event.new_state.attributes.get(position_attribute)
        command = self._get_pending_command(entity_id)
        if command is None:
            last_command = self.last_commands.get(entity_id)
            if (
                position is not None
                and last_command is not None
                and abs(position - last_command.target) <= self.position_tolerance
            ):
                return True
            if self.ignore_intermediate_states and event.new_state.state in [
                "opening",
                "closing",
            ]:
                self.logger.debug(
                    "Ignoring intermediate state change for %s", entity_id
                )
                return True
            return False
        if position is None:
            return True

        distance = abs(position - command.target)
        if distance <= self.position_tolerance:
            self.pending_commands.pop(entity_id, None)
            self.logger.debug(
                "Command target %s reached by %s at position %s",
                command.target,
                entity_id,
                position,
            )
            return True

        if event.old_state.state in ["opening", "closing"] and (
            event.new_state.state not in ["opening", "closing"]
        ):
            self.pending_commands.pop(entity_id, None)
            self.logger.debug(
                "Cover %s stopped at %s before reaching SAC target %s",
                entity_id,
                position,
                command.target,
            )
            return False

        previous_position = command.last_position
        previous_distance = abs(previous_position - command.target)
        if distance < previous_distance:
            command.last_position = position
            command.last_progress_at = dt_util.utcnow()
            self.logger.debug(
                "Cover %s progressed toward %s from %s to %s",
                entity_id,
                command.target,
                previous_position,
                position,
            )
            return True
        if distance == previous_distance:
            return True

        self.pending_commands.pop(entity_id, None)
        self.logger.debug(
            "Cover %s moved away from SAC target %s from %s to %s",
            entity_id,
            command.target,
            previous_position,
            position,
        )
        return False

    def _get_pending_command(self, entity_id: str) -> CoverCommand | None:
        """Return a command that has reported progress within the timeout."""
        command = self.pending_commands.get(entity_id)
        if command is None:
            return None
        if dt_util.utcnow() < command.expires_at:
            return command

        self.pending_commands.pop(entity_id, None)
        self.logger.debug(
            "Command to move %s to %s expired after no forward progress",
            entity_id,
            command.target,
        )
        return None

    def _serialize_pending_commands(self) -> dict[str, dict[str, str | int]]:
        """Remove expired commands and serialize those still in transit."""
        for entity_id in tuple(self.pending_commands):
            self._get_pending_command(entity_id)
        return self._serialize_commands(self.pending_commands)

    @staticmethod
    def _serialize_commands(
        commands: dict[str, CoverCommand],
    ) -> dict[str, dict[str, str | int]]:
        """Convert command records into Home Assistant state attributes."""
        return {
            entity_id: {
                "target": command.target,
                "source": command.source.value,
                "issued_at": command.issued_at.isoformat(),
                "last_progress_at": command.last_progress_at.isoformat(),
                "expires_at": command.expires_at.isoformat(),
            }
            for entity_id, command in commands.items()
        }

    @callback
    def _async_cancel_update_listener(self) -> None:
        """Cancel the scheduled update."""
        if self._update_listener:
            self._update_listener()
            self._update_listener = None

    async def async_timed_end_time(self) -> None:
        """Control state at end time."""
        self.logger.debug("Scheduling end time update at %s", self._end_time)
        self._async_cancel_update_listener()
        self.logger.debug(
            "End time: %s, Track end time: %s, Scheduled time: %s, Condition: %s",
            self._end_time,
            self._track_end_time,
            self._scheduled_time,
            self._end_time > self._scheduled_time,
        )
        self._update_listener = async_track_point_in_time(
            self.hass, self.async_timed_refresh, self._end_time
        )
        self._scheduled_time = self._end_time

    async def _async_update_data(self) -> AdaptiveCoverData:
        self.logger.debug("Updating data")
        options = self.config_entry.options
        self._update_options(options)
        self._update_external_override()
        self._update_datetime_objects()

        # Get data for the blind
        cover_data = self.get_blind_data(options=options)

        if not self.manual_toggle:
            for entity_id in self.manager.manual_controlled:
                self.manager.reset(entity_id)

        # calculate the state of the cover
        self.normal_cover_state = NormalCoverState(cover_data)
        self.logger.debug(
            "Determined normal cover state to be %s", self.normal_cover_state
        )

        self.default_state = round(self.normal_cover_state.get_state())
        self.logger.debug("Determined default state to be %s", self.default_state)
        state = self.state

        expired_manual_covers = self.manager.reset_if_needed()

        if (
            self._end_time
            and self._track_end_time
            and self._end_time > self._scheduled_time
        ):
            await self.async_timed_end_time()

        if self.state_change:
            await self.async_handle_state_change()
        if self.timed_refresh:
            await self.async_handle_timed_refresh()

        if self.control_toggle:
            for entity in expired_manual_covers:
                await self.async_apply_target(entity, immediate=True)
        self._update_control_method()

        normal_cover = self.normal_cover_state.cover
        # Run the solar_times method in a separate thread
        if (
            self._sun_start_time is None
            or dt_util.utcnow().date() != self._sun_start_time.date()
        ):
            self.logger.debug("Calculating solar times")
            loop = asyncio.get_running_loop()
            start, end = await loop.run_in_executor(None, normal_cover.solar_times)
            self._sun_start_time = start
            self._sun_end_time = end
            self.logger.debug("Sun start time: %s, Sun end time: %s", start, end)
        else:
            start, end = self._sun_start_time, self._sun_end_time
        return AdaptiveCoverData(
            states={
                "state": state,
                "start": start,
                "end": end,
                "control": self.control_method,
                "sun_motion": normal_cover.valid,
                "manual_override": self.manager.binary_cover_manual,
                "manual_overrides": self.manual_override_details,
            },
            attributes={
                "default": options.get(CONF_DEFAULT_HEIGHT),
                "sunset_default": options.get(CONF_SUNSET_POS),
                "sunset_offset": options.get(CONF_SUNSET_OFFSET),
                "azimuth_window": options.get(CONF_AZIMUTH),
                "field_of_view": [
                    options.get(CONF_FOV_LEFT),
                    options.get(CONF_FOV_RIGHT),
                ],
                "blind_spot": options.get(CONF_BLIND_SPOT_ELEVATION),
                "solar_position": self.solar_state,
                "position_tolerance": self.position_tolerance,
                "override_entity": self.override_entity,
                "override_state": self.external_override.raw_state,
                "override_target": self.external_override.target,
                "override_force": self.external_override.force,
                "override_reason": self.external_override.reason,
                "pending_commands": self._serialize_pending_commands(),
                "last_commands": self._serialize_commands(self.last_commands),
            },
        )

    async def async_handle_state_change(self) -> None:
        """Apply the current target after a tracked entity changes."""
        if self.control_toggle:
            for cover in self.entities:
                await self.async_apply_target(cover)
        self.state_change = False

    async def async_reset_manual_overrides(self, entities: set[str]) -> None:
        """Reset manual ownership and resume the affected covers."""
        reset_entities = entities.intersection(self.manager.manual_controlled)
        if not reset_entities:
            return

        for entity in reset_entities:
            self.manager.reset(entity)
            if self.control_toggle:
                await self.async_apply_target(entity, immediate=True)
        await self.async_refresh()

    async def async_handle_timed_refresh(self) -> None:
        """Apply the configured position at the end of the control period."""
        self.timed_refresh = False
        if not self.control_toggle:
            return

        if self.external_override.mode is not OverrideMode.AUTO:
            for cover in self.entities:
                await self.async_apply_target(cover, immediate=True)
            return

        target = self.config_entry.options.get(CONF_SUNSET_POS)
        if self._inverse_state:
            target = inverse_state(target)

        for cover in self.entities:
            if not self.manager.is_cover_manual(cover):
                await self.async_set_position(cover, target, CommandSource.TIMED_END)

    async def async_apply_target(self, entity: str, *, immediate: bool = False) -> None:
        """Apply the current external or solar target to one cover."""
        override = self.external_override
        if override.holds_commands:
            return

        if override.target is not None:
            if self.manager.is_cover_manual(entity) and not override.force:
                return
            source = (
                CommandSource.FORCED_EXTERNAL_OVERRIDE
                if override.force
                else CommandSource.EXTERNAL_OVERRIDE
            )
            await self.async_set_position(entity, override.target, source)
            return

        if self.manager.is_cover_manual(entity) or not self.check_adaptive_time:
            return

        target = self.solar_state
        options = self.config_entry.options
        if not self.check_position_delta(entity, target, options):
            return
        if not immediate and not self.check_time_delta(entity):
            return

        await self.async_set_position(entity, target, CommandSource.SOLAR)

    async def async_set_position(
        self,
        entity: str,
        state: int,
        source: CommandSource,
    ) -> None:
        """Call a cover service and record the expected resulting movement."""
        pending_command = self._get_pending_command(entity)
        if pending_command is not None and pending_command.target == state:
            return

        current_position = self._get_current_position(entity)
        if current_position is None or current_position == state:
            return

        service = SERVICE_SET_COVER_POSITION
        position_attribute = ATTR_POSITION
        if self._cover_type == SensorType.TILT:
            service = SERVICE_SET_COVER_TILT_POSITION
            position_attribute = ATTR_TILT_POSITION

        service_data = {
            ATTR_ENTITY_ID: entity,
            position_attribute: state,
        }
        issued_at = dt_util.utcnow()
        context = Context()
        command = CoverCommand(
            target=state,
            source=source,
            issued_at=issued_at,
            last_progress_at=issued_at,
            last_position=current_position,
            context_id=context.id,
        )
        self.pending_commands[entity] = command
        self.logger.debug("Run %s with data %s", service, service_data)
        try:
            await self.hass.services.async_call(
                COVER_DOMAIN,
                service,
                service_data,
                blocking=True,
                context=context,
            )
        except HomeAssistantError:
            self.pending_commands.pop(entity, None)
            self.logger.exception("Failed to send cover command to %s", entity)
            return

        self.last_commands[entity] = command

    @property
    def manual_override_details(self) -> dict[str, dict[str, str | int | None]]:
        """Return per-cover manual expiry and physical position details."""
        now = dt_util.utcnow()
        details = {}
        for entity_id in self.manager.manual_controlled:
            started_at = self.manager.manual_control_time[entity_id]
            expires_at = self.manager.expires_at(entity_id)
            details[entity_id] = {
                "held_position": self._get_current_position(entity_id),
                "started_at": started_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "remaining_seconds": max(0, int((expires_at - now).total_seconds())),
            }
        return details

    def _update_options(self, options):
        """Update options."""
        self.entities = options.get(CONF_ENTITIES, [])
        self.min_change = options.get(CONF_DELTA_POSITION, 1)
        self.position_tolerance = options.get(CONF_POSITION_TOLERANCE, 0)
        self.time_threshold = options.get(CONF_DELTA_TIME, 2)
        self.start_time = options.get(CONF_START_TIME)
        self.start_time_entity = options.get(CONF_START_ENTITY)
        self.override_entity = options.get(CONF_OVERRIDE_ENTITY)
        self.end_time = options.get(CONF_END_TIME)
        self.end_time_entity = options.get(CONF_END_ENTITY)
        self.manual_reset = options.get(CONF_MANUAL_OVERRIDE_RESET, False)
        self.manual_threshold = options.get(CONF_MANUAL_THRESHOLD)
        self.start_value = options.get(CONF_INTERP_START)
        self.end_value = options.get(CONF_INTERP_END)
        self.normal_list = options.get(CONF_INTERP_LIST)
        self.new_list = options.get(CONF_INTERP_LIST_NEW)

    def _update_external_override(self) -> None:
        """Read and normalize the configured external override entity."""
        if self.override_entity is None:
            self.external_override = ExternalOverride(mode=OverrideMode.AUTO)
            return
        self.external_override = parse_external_override(
            self.hass.states.get(self.override_entity)
        )

    def _update_control_method(self) -> None:
        """Set the control method exposed by the coordinator."""
        override = self.external_override
        if not self.control_toggle:
            self.control_method = "disabled"
        elif override.force:
            self.control_method = "forced_external_override"
        elif self.manager.binary_cover_manual:
            self.control_method = "manual"
        elif override.target is not None:
            self.control_method = "external_override"
        elif override.mode == OverrideMode.HOLD:
            self.control_method = "external_hold"
        elif override.mode == OverrideMode.UNAVAILABLE:
            self.control_method = "override_unavailable"
        elif override.mode == OverrideMode.INVALID:
            self.control_method = "override_invalid"
        else:
            self.control_method = "solar"

    def _update_datetime_objects(self) -> None:
        """Calculate and store start and end time datetimes."""
        start_time_str = None
        if self.start_time_entity:
            start_time_str = get_safe_state(self.hass, self.start_time_entity)
        elif self.start_time:
            start_time_str = self.start_time

        self._start_time = (
            get_datetime_from_str(start_time_str) if start_time_str else None
        )

        end_time_str = None
        if self.end_time_entity:
            end_time_str = get_safe_state(self.hass, self.end_time_entity)
        elif self.end_time:
            end_time_str = self.end_time

        if end_time_str:
            time = get_datetime_from_str(end_time_str)
            if time and time.time() == dt.time(0, 0):
                time += dt.timedelta(days=1)
            self._end_time = time
        else:
            self._end_time = None

    def get_blind_data(self, options):
        """Assign correct class for type of blind."""
        config = CoverConfig()
        self.common_data(options, config)
        if self._cover_type == SensorType.BLIND:
            self.vertical_data(options, config)
            cover_data = AdaptiveVerticalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                config,
            )
        if self._cover_type == SensorType.AWNING:
            self.vertical_data(options, config)
            self.horizontal_data(options, config)
            cover_data = AdaptiveHorizontalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                config,
            )
        if self._cover_type == SensorType.TILT:
            self.tilt_data(options, config)
            cover_data = AdaptiveTiltCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                config,
            )
        return cover_data

    @property
    def check_adaptive_time(self):
        """Check if time is within start and end times."""
        if self._start_time and self._end_time and self._start_time > self._end_time:
            self.logger.error("Start time is after end time")
        return self.before_end_time and self.after_start_time

    @property
    def after_start_time(self):
        """Check if the current time is after the start time."""
        if self._start_time is None:
            return True
        now = dt.datetime.now()
        self.logger.debug(
            "Start time: %s, now: %s, now >= time: %s",
            self._start_time,
            now,
            now >= self._start_time,
        )
        return now >= self._start_time

    @property
    def before_end_time(self):
        """Check if time is before end time."""
        if self._end_time is not None:
            now = dt.datetime.now()
            self.logger.debug(
                "End time: %s, now: %s, now < time: %s",
                self._end_time,
                now,
                now < self._end_time,
            )
            return now < self._end_time
        return True

    def _get_current_position(self, entity) -> int | None:
        """Get current position of cover."""
        state = self.hass.states.get(entity)
        if state is None:
            return None
        attribute = (
            "current_tilt_position"
            if self._cover_type == SensorType.TILT
            else "current_position"
        )
        return state.attributes.get(attribute)

    def check_position_delta(self, entity, state: int, options):
        """Check cover positions to reduce calls."""
        position = self._get_current_position(entity)
        if position is not None:
            condition = abs(position - state) >= self.min_change
            self.logger.debug(
                "Entity: %s,  position: %s, state: %s, delta position: %s, min_change: %s, condition: %s",
                entity,
                position,
                state,
                abs(position - state),
                self.min_change,
                condition,
            )
            if state in [
                options.get(CONF_SUNSET_POS),
                options.get(CONF_DEFAULT_HEIGHT),
                0,
                100,
            ]:
                condition = True
            return condition
        return True

    def check_time_delta(self, entity):
        """Check if time delta is passed."""
        now = dt_util.utcnow()
        last_updated = get_last_updated(entity, self.hass)
        if last_updated is not None:
            condition = now - last_updated >= dt.timedelta(minutes=self.time_threshold)
            self.logger.debug(
                "Entity: %s, time delta: %s, threshold: %s, condition: %s",
                entity,
                now - last_updated,
                self.time_threshold,
                condition,
            )
            return condition
        return True

    @property
    def pos_sun(self):
        """Fetch information for sun position."""
        state = self.hass.states.get("sun.sun")
        if state is None:
            return [None, None]
        return [state.attributes.get("azimuth"), state.attributes.get("elevation")]

    def common_data(self, options, config):
        """Update shared parameters."""
        config.sunset_pos = options.get(CONF_SUNSET_POS)
        config.sunset_off = options.get(CONF_SUNSET_OFFSET)
        config.sunrise_off = options.get(
            CONF_SUNRISE_OFFSET, options.get(CONF_SUNSET_OFFSET)
        )
        config.timezone = self.hass.config.time_zone
        config.fov_left = options.get(CONF_FOV_LEFT)
        config.fov_right = options.get(CONF_FOV_RIGHT)
        config.win_azi = options.get(CONF_AZIMUTH)
        config.h_def = options.get(CONF_DEFAULT_HEIGHT)
        config.max_pos = options.get(CONF_MAX_POSITION)
        config.min_pos = options.get(CONF_MIN_POSITION)
        config.apply_max_limit_on_sun = options.get(CONF_ENABLE_MAX_POSITION, False)
        config.apply_min_limit_on_sun = options.get(CONF_ENABLE_MIN_POSITION, False)
        config.blind_spot_left = options.get(CONF_BLIND_SPOT_LEFT)
        config.blind_spot_right = options.get(CONF_BLIND_SPOT_RIGHT)
        config.blind_spot_elevation = options.get(CONF_BLIND_SPOT_ELEVATION)
        config.blind_spot_on = options.get(CONF_ENABLE_BLIND_SPOT, False)
        config.min_elevation = options.get(CONF_MIN_ELEVATION, None)
        config.max_elevation = options.get(CONF_MAX_ELEVATION, None)
        return config

    def vertical_data(self, options, config):
        """Update data for vertical blinds."""
        config.distance = options.get(CONF_DISTANCE)
        config.h_win = options.get(CONF_HEIGHT_WIN)
        return config

    def horizontal_data(self, options, config):
        """Update data for horizontal blinds."""
        config.awn_length = options.get(CONF_LENGTH_AWNING)
        config.awn_angle = options.get(CONF_AWNING_ANGLE)
        return config

    def tilt_data(self, options, config):
        """Update data for tilted blinds."""
        config.slat_distance = options.get(CONF_TILT_DISTANCE)
        config.depth = options.get(CONF_TILT_DEPTH)
        config.mode = options.get(CONF_TILT_MODE)
        return config

    @property
    def state(self) -> int:
        """Return the external target or calculated solar position."""
        if self.external_override.target is not None:
            self.logger.debug(
                "Using external override position: %s",
                self.external_override.target,
            )
            return self.external_override.target
        return self.solar_state

    @property
    def solar_state(self) -> int:
        """Return the calibrated position calculated from the sun."""
        state = self.default_state
        self.logger.debug("Starting with solar position: %s", state)

        if self._use_interpolation:
            self.logger.debug("Interpolating position: %s", state)
            state = self.interpolate_states(state)

        if self._inverse_state:
            if self._use_interpolation:
                self.logger.info(
                    "Inverse state is not supported with interpolation, you can inverse the state by arranging the list from high to low"
                )
            else:
                state = inverse_state(state)
                self.logger.debug("Inversed position: %s", state)

        final_state = round(state)
        self.logger.debug("Final solar position to use: %s", final_state)
        return final_state

    def interpolate_states(self, state):
        """Interpolate states."""
        normal_range = [0, 100]
        new_range = []
        # Allow partial range overrides by falling back to defaults
        if self.start_value is not None or self.end_value is not None:
            start = self.start_value if self.start_value is not None else 0
            end = self.end_value if self.end_value is not None else 100
            new_range = [start, end]
        if self.normal_list and self.new_list:
            normal_range = list(map(int, self.normal_list))
            new_range = list(map(int, self.new_list))
        if new_range:
            state = np.interp(state, normal_range, new_range)
            if state == new_range[0]:
                state = 0
            if state == new_range[-1]:
                state = 100
        return state

    @property
    def control_toggle(self):
        """Toggle automation."""
        return self._control_toggle

    @control_toggle.setter
    def control_toggle(self, value):
        self._control_toggle = value

    @property
    def manual_toggle(self):
        """Toggle automation."""
        return self._manual_toggle

    @manual_toggle.setter
    def manual_toggle(self, value):
        self._manual_toggle = value


def inverse_state(state: int) -> int:
    """Inverse state."""
    return 100 - state
