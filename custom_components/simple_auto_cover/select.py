"""Select entity to force cover position."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FORCE_MODE
from .coordinator import AdaptiveDataUpdateCoordinator

OPTIONS = ["auto", "force open", "force close"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entity."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SimpleAutoCoverSelect(entry, coordinator)])


class SimpleAutoCoverSelect(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SelectEntity
):
    """Select entity to force cover position."""

    _attr_options = OPTIONS
    _attr_has_entity_name = True
    _attr_translation_key = FORCE_MODE

    def __init__(
        self, entry: ConfigEntry, coordinator: AdaptiveDataUpdateCoordinator
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_force_mode"
        self.coordinator = coordinator

    @property
    def current_option(self) -> str:
        """Return the currently selected option."""
        return self.coordinator.force_mode

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self.coordinator.force_mode = option
        await self.coordinator.async_refresh()
