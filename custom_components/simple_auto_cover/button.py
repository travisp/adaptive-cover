"""Button platform for the Simple Auto Cover integration."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    _LOGGER,
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
    """Set up the button platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    reset_manual = AdaptiveCoverButton(
        config_entry, config_entry.entry_id, "Reset Manual Override", coordinator
    )

    buttons = []

    entities = config_entry.options.get(CONF_ENTITIES, [])
    if len(entities) >= 1:
        buttons = [reset_manual]

    async_add_entities(buttons)


class AdaptiveCoverButton(AdaptiveCoverEntity, ButtonEntity):
    """Representation of a simple auto cover button."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cog-refresh-outline"

    def __init__(
        self,
        config_entry,
        unique_id: str,
        button_name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the button."""
        super().__init__(config_entry, unique_id, coordinator)
        self._attr_unique_id = f"{unique_id}_{button_name}"
        self._button_name = button_name
        self._entities = config_entry.options.get(CONF_ENTITIES, [])

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._button_name} {self._name}"

    async def async_press(self) -> None:
        """Handle the button press."""
        for entity in self._entities:
            if self.coordinator.manager.is_cover_manual(entity):
                _LOGGER.debug("Resetting manual override for: %s", entity)
                await self.coordinator.async_set_position(
                    entity, self.coordinator.state
                )
                while self.coordinator.wait_for_target.get(entity):
                    await asyncio.sleep(1)
                self.coordinator.manager.reset(entity)
            else:
                _LOGGER.debug(
                    "Resetting manual override for %s is not needed since it is already auto-controlled",
                    entity,
                )
        await self.coordinator.async_refresh()
