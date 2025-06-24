"""Basic integration test for Simple Auto Cover."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import custom_components.simple_auto_cover as sac
except Exception as exc:
    pytest.fail(f"Integration failed to load: {exc}")


def test_import_success():
    """Ensure the integration imports without errors."""
    assert sac.DOMAIN == "simple_auto_cover"


class DummyConfigEntries:
    """Mock of Home Assistant's config entries helper."""

    def __init__(self):
        """Initialize storage for recorded actions."""
        self.forwarded = []
        self.unloaded = []
        self.reloaded = None

    async def async_forward_entry_setups(self, entry, platforms):
        """Record forwarded setups."""
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry, platforms):
        """Record unloaded platforms."""
        self.unloaded.append((entry, platforms))
        return True

    async def async_reload(self, entry_id):
        """Record a reload request."""
        self.reloaded = entry_id


class DummyHass:
    """Very small subset of :class:`homeassistant.core.HomeAssistant`."""

    def __init__(self):
        """Initialize the dummy Home Assistant object."""
        self.config_entries = DummyConfigEntries()
        self.data = {}


class DummyEntry:
    """Mimic a config entry object."""

    def __init__(self, entry_id="1", data=None, options=None):
        """Create a new dummy entry."""
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}
        self.update_listeners = []
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        """Register a callback to run on unload."""
        self.unload_callbacks.append(callback)

    def add_update_listener(self, listener):
        """Track listener registration."""
        self.update_listeners.append(listener)
        return listener


class DummyCoordinator:
    """Stubbed coordinator used during integration tests."""

    def __init__(self, hass):
        """Initialize the dummy coordinator."""
        self.hass = hass
        self.first_refresh = False

    async def async_config_entry_first_refresh(self):
        """Simulate the first refresh logic."""
        self.first_refresh = True

    async def async_check_entity_state_change(self, *args, **kwargs):
        """Mock handler for entity state changes."""
        pass

    async def async_check_cover_state_change(self, *args, **kwargs):
        """Mock handler for cover state changes."""
        pass


@pytest.mark.asyncio
async def test_initialize_and_lifecycle(monkeypatch):
    """Test setup and unload of the integration entry."""

    hass = DummyHass()
    entry = DummyEntry(options={sac.CONF_ENTITIES: ["cover.test"]})

    track_calls = []

    def dummy_track_state_change_event(hass_obj, entities, callback):
        track_calls.append(list(entities))
        return lambda: None

    monkeypatch.setattr(
        sac, "async_track_state_change_event", dummy_track_state_change_event
    )
    monkeypatch.setattr(sac, "AdaptiveDataUpdateCoordinator", DummyCoordinator)

    assert await sac.async_initialize_integration(hass) is True

    assert await sac.async_setup_entry(hass, entry) is True
    assert sac.DOMAIN in hass.data
    assert entry.entry_id in hass.data[sac.DOMAIN]
    coord = hass.data[sac.DOMAIN][entry.entry_id]
    assert isinstance(coord, DummyCoordinator) and coord.first_refresh
    assert track_calls == [["sun.sun"], ["cover.test"]]
    assert hass.config_entries.forwarded == [(entry, sac.PLATFORMS)]

    listener = entry.update_listeners[0]
    await listener(hass, entry)
    assert hass.config_entries.reloaded == entry.entry_id

    assert await sac.async_unload_entry(hass, entry) is True
    assert hass.config_entries.unloaded == [(entry, sac.PLATFORMS)]
    assert entry.entry_id not in hass.data[sac.DOMAIN]
