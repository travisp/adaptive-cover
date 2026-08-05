"""Simple Auto Cover integration diagnostics."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SimpleAutoCoverDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    """Return config entry diagnostics."""
    coordinator: SimpleAutoCoverDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    return {
        "title": "Simple Auto Cover Configuration",
        "type": "config_entry",
        "identifier": config_entry.entry_id,
        "config_data": dict(config_entry.data),
        "config_options": dict(config_entry.options),
        "manual_overrides": coordinator.manual_override_details,
        "pending_commands": coordinator.data.attributes["pending_commands"],
        "last_commands": coordinator.data.attributes["last_commands"],
    }
