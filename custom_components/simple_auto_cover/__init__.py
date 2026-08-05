"""The Simple Auto Cover integration."""

from __future__ import annotations

from functools import partial

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME, EVENT_CALL_SERVICE, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_END_ENTITY,
    CONF_ENTITIES,
    CONF_OVERRIDE_ENTITY,
    DOMAIN,
    SERVICE_RESET_MANUAL_OVERRIDE,
    _LOGGER,
)
from .coordinator import SimpleAutoCoverDataUpdateCoordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]
RESET_MANUAL_OVERRIDE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids})


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up integration services."""
    hass.data[DOMAIN] = {}
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_MANUAL_OVERRIDE,
        partial(_async_reset_manual_override, hass),
        schema=RESET_MANUAL_OVERRIDE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Simple Auto Cover from a config entry."""

    coordinator = SimpleAutoCoverDataUpdateCoordinator(hass)
    cover_entities = entry.options.get(CONF_ENTITIES, [])
    end_time_entity = entry.options.get(CONF_END_ENTITY)
    override_entity = entry.options.get(CONF_OVERRIDE_ENTITY)
    tracked_entities = ["sun.sun"]
    for entity_id in (end_time_entity, override_entity):
        if entity_id is not None and entity_id not in tracked_entities:
            tracked_entities.append(entity_id)

    _LOGGER.debug("Setting up entry %s", entry.data.get(CONF_NAME))

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            tracked_entities,
            coordinator.async_check_entity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            cover_entities,
            coordinator.async_check_cover_state_change,
        )
    )
    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_CALL_SERVICE,
            coordinator.handle_cover_service_call,
        )
    )

    await coordinator.async_restore_manual_control()
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: SimpleAutoCoverDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    await coordinator.async_save_manual_control()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_reset_manual_override(hass: HomeAssistant, call: ServiceCall) -> None:
    """Reset manual ownership for the requested physical covers."""
    entities = set(call.data[ATTR_ENTITY_ID])
    for coordinator in hass.data[DOMAIN].values():
        await coordinator.async_reset_manual_overrides(entities)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
