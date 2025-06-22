"""Helper functions."""

from __future__ import annotations

import datetime as dt

from dateutil import parser
from homeassistant.core import HomeAssistant


def get_safe_state(hass: HomeAssistant, entity_id: str):
    """Get a safe state value if not available."""
    state = hass.states.get(entity_id)
    if not state or state.state in ["unknown", "unavailable"]:
        return None
    return state.state


def get_datetime_from_str(string: str | None) -> dt.datetime | None:
    """Convert datetime string to datetime."""
    if string is not None:
        return parser.parse(string, ignoretz=True)
    return None


def get_last_updated(entity_id: str | None, hass: HomeAssistant) -> dt.datetime | None:
    """Get last updated attribute from entity."""
    if entity_id is not None:
        state = hass.states.get(entity_id)
        if state:
            return state.last_updated
    return None
