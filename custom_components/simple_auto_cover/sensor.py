"""Sensor platform for Simple Auto Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SENSOR_TYPE, DOMAIN
from .coordinator import SimpleAutoCoverDataUpdateCoordinator
from .entity import SimpleAutoCoverEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Simple Auto Cover config entry."""

    name = config_entry.data[CONF_NAME]
    coordinator: SimpleAutoCoverDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    sensor = SimpleAutoCoverSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )
    start = SimpleAutoCoverTimeSensorEntity(
        config_entry.entry_id,
        hass,
        config_entry,
        name,
        "Start Sun",
        "start",
        "mdi:sun-clock-outline",
        coordinator,
    )
    end = SimpleAutoCoverTimeSensorEntity(
        config_entry.entry_id,
        hass,
        config_entry,
        name,
        "End Sun",
        "end",
        "mdi:sun-clock",
        coordinator,
    )
    control = SimpleAutoCoverControlSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )
    async_add_entities([sensor, start, end, control])


class SimpleAutoCoverSensorEntity(SimpleAutoCoverEntity, SensorEntity):
    """Simple Auto Cover Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: SimpleAutoCoverDataUpdateCoordinator,
    ) -> None:
        """Initialize simple_auto_cover Sensor."""
        super().__init__(config_entry, unique_id, coordinator)
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._sensor_name = "Cover Position"
        self._attr_unique_id = f"{unique_id}_{self._sensor_name}"
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states["state"]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        return self.data.attributes


class SimpleAutoCoverTimeSensorEntity(SimpleAutoCoverEntity, SensorEntity):
    """Simple Auto Cover Time Sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        sensor_name: str,
        key: str,
        icon: str,
        coordinator: SimpleAutoCoverDataUpdateCoordinator,
    ) -> None:
        """Initialize simple_auto_cover Sensor."""
        super().__init__(config_entry, unique_id, coordinator)
        self._attr_icon = icon
        self.key = key
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_unique_id = f"{unique_id}_{sensor_name}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._cover_type = self.config_entry.data[CONF_SENSOR_TYPE]
        self._sensor_name = sensor_name
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states[self.key]


class SimpleAutoCoverControlSensorEntity(SimpleAutoCoverEntity, SensorEntity):
    """Simple Auto Cover Control method Sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "control"

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: SimpleAutoCoverDataUpdateCoordinator,
    ) -> None:
        """Initialize simple_auto_cover Sensor."""
        super().__init__(config_entry, unique_id, coordinator)
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._sensor_name = "Control Method"
        self._attr_unique_id = f"{unique_id}_{self._sensor_name}"
        self._device_id = unique_id
        self.id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._cover_type = self.config_entry.data[CONF_SENSOR_TYPE]
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self.data.states["control"]
