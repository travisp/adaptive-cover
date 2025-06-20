"""System tests for the Simple Auto Cover integration."""

from __future__ import annotations

import importlib
import sys
import pytest

# Ensure the real Home Assistant package is used for this integration test.
pytest.importorskip("homeassistant")
for name in [m for m in list(sys.modules) if m.startswith("homeassistant")]:
    sys.modules.pop(name)
importlib.invalidate_caches()

try:  # pragma: no cover - fail if Home Assistant is missing
    from homeassistant.config_entries import ConfigEntryState
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except Exception as exc:  # pragma: no cover - not installed
    pytest.fail(f"Home Assistant not available: {exc}")

from custom_components.simple_auto_cover import DOMAIN
from custom_components.simple_auto_cover.const import (
    CONF_AZIMUTH,
    CONF_DEFAULT_HEIGHT,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_MODE,
    CONF_SENSOR_TYPE,
    SensorType,
)


@pytest.mark.asyncio
async def test_full_setup_and_unload(hass):
    """Test setting up and unloading the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Test", CONF_SENSOR_TYPE: SensorType.BLIND},
        options={
            CONF_MODE: "basic",
            CONF_AZIMUTH: 180,
            CONF_FOV_LEFT: 90,
            CONF_FOV_RIGHT: 90,
            CONF_DEFAULT_HEIGHT: 60,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert DOMAIN in hass.data

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
