"""Binary Sensor platform for the Simple Auto Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator
from .entity import AdaptiveCoverEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Simple Auto Cover binary sensor platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    binary_sensor = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Sun Infront",
        False,
        "sun_motion",
        BinarySensorDeviceClass.MOTION,
        coordinator,
    )
    manual_override = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Manual Override",
        False,
        "manual_override",
        BinarySensorDeviceClass.RUNNING,
        coordinator,
    )
    async_add_entities([binary_sensor, manual_override])


class AdaptiveCoverBinarySensor(AdaptiveCoverEntity, BinarySensorEntity):
    """Representation of a simple auto cover binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        binary_name: str,
        state: bool,
        key: str,
        device_class: BinarySensorDeviceClass,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(config_entry, unique_id, coordinator)
        self._key = key
        self._attr_translation_key = key
        self._binary_name = binary_name
        self._attr_unique_id = f"{unique_id}_{binary_name}"
        self._state = state
        self._attr_device_class = device_class

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._binary_name} {self._name}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.states[self._key]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        if self._key == "manual_override":
            details = self.coordinator.data.states["manual_overrides"]
            return {
                "manual_controlled": list(details),
                "manual_overrides": details,
            }
