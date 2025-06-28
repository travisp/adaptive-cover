"""Unit tests for the entity helpers."""

import types
import pytest

from homeassistant.const import CONF_NAME
from custom_components.simple_auto_cover.const import (
    CONF_ENTITIES,
    CONF_SENSOR_TYPE,
    COVER_TYPE_DISPLAY,
    DOMAIN,
    SensorType,
)


@pytest.fixture
def entity_module():
    """Return the entity module for import testing."""
    import custom_components.simple_auto_cover.entity as entity

    return entity


@pytest.fixture
def button_module():
    """Return the button module for import testing."""
    import custom_components.simple_auto_cover.button as button

    return button


@pytest.fixture
def binary_sensor_module():
    """Return the binary sensor module for import testing."""
    import custom_components.simple_auto_cover.binary_sensor as binary_sensor

    return binary_sensor


@pytest.fixture
def sensor_module():
    """Return the sensor module for import testing."""
    import custom_components.simple_auto_cover.sensor as sensor

    return sensor


@pytest.fixture
def switch_module():
    """Return the switch module for import testing."""
    import custom_components.simple_auto_cover.switch as switch

    return switch


@pytest.fixture
def select_module():
    """Return the select module for import testing."""
    import custom_components.simple_auto_cover.select as select

    return select


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
        data={CONF_NAME: name, CONF_SENSOR_TYPE: sensor_type or SensorType.BLIND},
        options={CONF_ENTITIES: ["cover.one"]},
        entry_id="1",
    )


def test_base_entity_initialization(entity_module):
    """Ensure base entity is initialized with the correct attributes."""
    entry = make_entry()
    coord = DummyCoordinator()
    entity = entity_module.SimpleAutoCoverEntity(entry, "uid", coord)

    assert entity._device_id == "uid"
    assert entity._name == entry.data[CONF_NAME]
    assert entity._device_name == COVER_TYPE_DISPLAY[entry.data[CONF_SENSOR_TYPE]]
    assert entity.device_info["identifiers"] == {(DOMAIN, "uid")}


def test_button_inherits_base(entity_module, button_module):
    """Verify button inherits from the base entity class."""
    entry = make_entry()
    coord = DummyCoordinator()
    button = button_module.SimpleAutoCoverButton(entry, "uid", "Reset", coord)

    assert isinstance(button, entity_module.SimpleAutoCoverEntity)
    assert button.name == "Reset " + entry.data[CONF_NAME]
    assert (
        button.device_info["name"] == COVER_TYPE_DISPLAY[entry.data[CONF_SENSOR_TYPE]]
    )
    assert button.unique_id == "uid_Reset"


def test_binary_sensor_is_on(entity_module, binary_sensor_module):
    """Confirm binary sensor reports its state correctly."""
    entry = make_entry()
    coord = DummyCoordinator(states={"sun": True, "manual_list": []})
    sensor = binary_sensor_module.SimpleAutoCoverBinarySensor(
        entry,
        "uid",
        "Sun",
        False,
        "sun",
        binary_sensor_module.BinarySensorDeviceClass.MOTION,
        coord,
    )

    assert isinstance(sensor, entity_module.SimpleAutoCoverEntity)
    assert sensor.is_on is True
    assert sensor.name == "Sun " + entry.data[CONF_NAME]
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

    sensor = sensor_module.SimpleAutoCoverSensorEntity(
        "uid", None, entry, entry.data[CONF_NAME], coord
    )

    assert sensor.native_value == 55
    assert sensor.extra_state_attributes == {"foo": "bar"}

    time_sensor = sensor_module.SimpleAutoCoverTimeSensorEntity(
        "uid",
        None,
        entry,
        entry.data[CONF_NAME],
        "Start Sun",
        "start",
        "icon",
        coord,
    )
    assert time_sensor.native_value == states["start"]

    control_sensor = sensor_module.SimpleAutoCoverControlSensorEntity(
        "uid", None, entry, entry.data[CONF_NAME], coord
    )

    assert control_sensor.native_value == "auto"


def test_switch_initial_state(entity_module, switch_module):
    """Check initial attributes of the manual override switch."""
    entry = make_entry()
    coord = DummyCoordinator()
    switch = switch_module.SimpleAutoCoverSwitch(
        entry,
        "uid",
        "Allow Manual Override",
        True,
        "manual_toggle",
        coord,
    )

    assert isinstance(switch, entity_module.AdaptiveCoverEntity)
    assert switch.name == "Allow Manual Override " + entry.data[CONF_NAME]
    assert switch.unique_id == "uid_manual_toggle"


@pytest.mark.asyncio
async def test_switch_async_setup_entry(switch_module):
    """Verify switch setup via platform helper."""
    entry = make_entry()
    hass = types.SimpleNamespace(data={DOMAIN: {entry.entry_id: DummyCoordinator()}})
    added: list = []

    await switch_module.async_setup_entry(hass, entry, added.extend)

    assert [e.name for e in added] == [
        f"Toggle Control {entry.data[CONF_NAME]}",
        f"Allow Manual Override {entry.data[CONF_NAME]}",
    ]
    assert sorted(e.unique_id for e in added) == [
        f"{entry.entry_id}_control_toggle",
        f"{entry.entry_id}_manual_toggle",
    ]


def test_control_sensor_manual(sensor_module):
    """Control sensor reports manual mode."""
    entry = make_entry()
    states = {"control": "manual"}
    coord = DummyCoordinator(states=states)
    control_sensor = sensor_module.SimpleAutoCoverControlSensorEntity(
        "uid", None, entry, entry.data[CONF_NAME], coord
    )

    assert control_sensor.native_value == "manual"


def test_control_sensor_force(sensor_module):
    """Control sensor reports force mode."""
    entry = make_entry()
    states = {"control": "force"}
    coord = DummyCoordinator(states=states)
    control_sensor = sensor_module.SimpleAutoCoverControlSensorEntity(
        "uid", None, entry, entry.data[CONF_NAME], coord
    )

    assert control_sensor.native_value == "force"


def test_select_initialization(entity_module, select_module):
    """Validate select entity inherits from the base and is named correctly."""
    entry = make_entry()
    coord = DummyCoordinator()

    select = select_module.SimpleAutoCoverSelect(entry, coord)

    assert isinstance(select, entity_module.SimpleAutoCoverEntity)
    assert select.name == "Force mode " + entry.data[CONF_NAME]
    assert select.unique_id == f"{entry.entry_id}_force_mode"

