"""Base entity for the Simple Auto Cover integration."""

from __future__ import annotations

from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SENSOR_TYPE, COVER_TYPE_DISPLAY, DOMAIN
from .coordinator import SimpleAutoCoverDataUpdateCoordinator


class SimpleAutoCoverEntity(CoordinatorEntity[SimpleAutoCoverDataUpdateCoordinator]):
    """Common entity base class for Simple Auto Cover."""

    def __init__(
        self,
        config_entry,
        unique_id: str,
        coordinator: SimpleAutoCoverDataUpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator=coordinator)
        self.type = COVER_TYPE_DISPLAY
        self.config_entry = config_entry
        self._name = config_entry.data[CONF_NAME]
        self._device_id = unique_id
        self._device_name = self.type[config_entry.data[CONF_SENSOR_TYPE]]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )
