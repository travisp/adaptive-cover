"""Helper functions."""

import datetime as dt

from dateutil import parser
from homeassistant.core import HomeAssistant


def get_safe_state(hass: HomeAssistant, entity_id: str):
    """Get a safe state value if not available."""
    state = hass.states.get(entity_id)
    if not state or state.state in ["unknown", "unavailable"]:
        return None
    return state.state

def get_datetime_from_str(string: str):
    """Convert datetime string to datetime."""
    if string is not None:
        return parser.parse(string, ignoretz=True)

def get_last_updated(entity_id: str, hass: HomeAssistant):
    """Get last updated attribute from entity."""
    if entity_id is not None:
        if hass.states.get(entity_id):
            return hass.states.get(entity_id).last_updated

def check_time_passed(time: dt.datetime):
    """Return ``True`` if ``time`` has already passed today."""
    now = dt.datetime.now().time()
    return now >= time.time()
