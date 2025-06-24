"""Unit tests for the entity helpers."""

import types
import pytest

from tests.conftest import import_module
from custom_components.simple_auto_cover import const


@pytest.fixture
def entity_module():
    """Return the entity module for import testing."""
    return import_module(
        "custom_components/simple_auto_cover/entity.py",
        "custom_components.simple_auto_cover.entity",
    )


@pytest.fixture
def button_module():
    """Return the button module for import testing."""
    return import_module(
        "custom_components/simple_auto_cover/button.py",
        "custom_components.simple_auto_cover.button",
    )


@pytest.fixture
def binary_sensor_module():
    """Return the binary sensor module for import testing."""
    return import_module(
        "custom_components/simple_auto_cover/binary_sensor.py",
        "custom_components.simple_auto_cover.binary_sensor",
    )


@pytest.fixture
def sensor_module():
    """Return the sensor module for import testing."""
    return import_module(
        "custom_components/simple_auto_cover/sensor.py",
        "custom_components.simple_auto_cover.sensor",
    )


@pytest.fixture
def switch_module():
    """Return the switch module for import testing."""
    return import_module(
        "custom_components/simple_auto_cover/switch.py",
        "custom_components.simple_auto_cover.switch",
    )


class DummyCoordinator:
    """Simplified coordinator for entity tests."""

    def __init__(self, states=None, attrs=None):
        """Initialize with optional state and attribute dictionaries."""
        self.data = types.SimpleNamespace(states=states or {}, attributes=attrs or {})
        self.last_update_success = True
        self.logger = types.SimpleNamespace(debug=lambda *a, **k: None)

    async def async_request_refresh(self):
        """Mock request of a data refresh."""
        pass

    async def async_refresh(self):
        """Mock refresh callback."""
        pass

    def async_add_listener(self, *_):
        """Return a dummy remove callback for listeners."""
        return lambda: None


def make_entry(*, name="Test", sensor_type=None):
    """Create a simple config entry namespace for tests."""
    return types.SimpleNamespace(
        data={
            "name": name,
            const.CONF_SENSOR_TYPE: sensor_type or const.SensorType.BLIND,
        },
        options={const.CONF_ENTITIES: ["cover.one"]},
        entry_id="1",
    )


def test_base_entity_initialization(entity_module):
    """Ensure base entity is initialized with the correct attributes."""
    entry = make_entry()
    coord = DummyCoordinator()
    entity = entity_module.AdaptiveCoverEntity(entry, "uid", coord)

    assert entity._device_id == "uid"
    assert entity._name == entry.data["name"]
    assert (
        entity._device_name
        == const.COVER_TYPE_DISPLAY[entry.data[const.CONF_SENSOR_TYPE]]
    )
    assert entity.device_info["identifiers"] == {(const.DOMAIN, "uid")}


def test_button_inherits_base(entity_module, button_module):
    """Verify button inherits from the base entity class."""
    entry = make_entry()
    coord = DummyCoordinator()
    button = button_module.AdaptiveCoverButton(entry, "uid", "Reset", coord)

    assert isinstance(button, entity_module.AdaptiveCoverEntity)
    assert button.name == "Reset " + entry.data["name"]
    assert (
        button.device_info["name"]
        == const.COVER_TYPE_DISPLAY[entry.data[const.CONF_SENSOR_TYPE]]
    )
    assert button.unique_id == "uid_Reset"


def test_binary_sensor_is_on(entity_module, binary_sensor_module):
    """Confirm binary sensor reports its state correctly."""
    entry = make_entry()
    coord = DummyCoordinator(states={"sun": True, "manual_list": []})
    sensor = binary_sensor_module.AdaptiveCoverBinarySensor(
        entry,
        "uid",
        "Sun",
        False,
        "sun",
        binary_sensor_module.BinarySensorDeviceClass.MOTION,
        coord,
    )

    assert isinstance(sensor, entity_module.AdaptiveCoverEntity)
    assert sensor.is_on is True
    assert sensor.name == "Sun " + entry.data["name"]
    assert sensor.unique_id == "uid_Sun"


def test_sensor_native_value(entity_module, sensor_module):
    """Validate sensor entities expose the expected values."""
    entry = make_entry()
    states = {
        "state": 55,
        "start": "2025-01-01",
        "end": "2025-01-02",
        "control": "auto",
    }
    coord = DummyCoordinator(states=states, attrs={"foo": "bar"})

    sensor = sensor_module.AdaptiveCoverSensorEntity(
        "uid", None, entry, entry.data["name"], coord
    )
    assert sensor.native_value == 55
    assert sensor.extra_state_attributes == {"foo": "bar"}

    time_sensor = sensor_module.AdaptiveCoverTimeSensorEntity(
        "uid",
        None,
        entry,
        entry.data["name"],
        "Start Sun",
        "start",
        "icon",
        coord,
    )
    assert time_sensor.native_value == states["start"]

    control_sensor = sensor_module.AdaptiveCoverControlSensorEntity(
        "uid", None, entry, entry.data["name"], coord
    )
    assert control_sensor.native_value == "auto"


def test_switch_initial_state(entity_module, switch_module):
    """Check initial attributes of the manual override switch."""
    entry = make_entry()
    coord = DummyCoordinator()
    switch = switch_module.AdaptiveCoverSwitch(
        entry, "uid", "Manual", True, "manual_toggle", coord
    )

    assert isinstance(switch, entity_module.AdaptiveCoverEntity)
    assert switch.name == "Manual " + entry.data["name"]
    assert switch.unique_id == "uid_Manual"
