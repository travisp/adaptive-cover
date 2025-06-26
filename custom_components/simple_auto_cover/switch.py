"""Switch platform for the Simple Auto Cover integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_ENTITIES,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .entity import AdaptiveCoverEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo switch platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    manual_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Allow Manual Override",
        True,
        "manual_toggle",
        coordinator,
    )
    control_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Toggle Control",
        True,
        "control_toggle",
        coordinator,
    )
    switches = []

    if len(config_entry.options.get(CONF_ENTITIES)) >= 1:
        switches = [control_switch, manual_switch]

    async_add_entities(switches)


class AdaptiveCoverSwitch(AdaptiveCoverEntity, SwitchEntity, RestoreEntity):
    """Representation of a simple auto cover switch."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        switch_name: str,
        initial_state: bool,
        key: str,
        coordinator: AdaptiveDataUpdateCoordinator,
        device_class: SwitchDeviceClass | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(config_entry, unique_id, coordinator)
        self._state: bool | None = None
        self._key = key
        self._attr_translation_key = key
        self._switch_name = switch_name
        self._attr_device_class = device_class
        self._initial_state = initial_state
        self._attr_unique_id = f"{unique_id}_{switch_name}"

        self.coordinator.logger.debug("Setup switch")

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._switch_name} {self._name}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.logger.debug("Turning on")
        self._attr_is_on = True
        setattr(self.coordinator, self._key, True)
        if self._key == "control_toggle" and kwargs.get("added") is not True:
            for entity in self.coordinator.entities:
                if (
                    not self.coordinator.manager.is_cover_manual(entity)
                    and self.coordinator.check_adaptive_time
                ):
                    await self.coordinator.async_set_position(
                        entity, self.coordinator.state
                    )
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.coordinator.logger.debug("Turning off")
        self._attr_is_on = False
        setattr(self.coordinator, self._key, False)
        if self._key == "control_toggle" and kwargs.get("added") is not True:
            for entity in self.coordinator.manager.manual_controlled:
                self.coordinator.manager.reset(entity)
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        self.coordinator.logger.debug("%s: last state is %s", self._name, last_state)
        if (last_state is None and self._initial_state) or (
            last_state is not None and last_state.state == STATE_ON
        ):
            await self.async_turn_on(added=True)
        else:
            await self.async_turn_off(added=True)
