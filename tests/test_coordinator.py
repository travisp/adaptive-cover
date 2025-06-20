"""Tests for the adaptive cover coordinator."""

import sys
import types
import math
import datetime as dt
from pathlib import Path
from importlib import util
import dataclasses


# Stub numpy functions used by the module
np_stub = types.ModuleType("numpy")
np_stub.interp = lambda x, xp, fp: fp[0] + (fp[1] - fp[0]) * (x - xp[0]) / (xp[1] - xp[0]) if xp[1] - xp[0] else fp[0]
np_stub.cos = math.cos
np_stub.sin = math.sin
np_stub.tan = math.tan
np_stub.clip = lambda x, low, high: max(min(x, high), low)
np_stub.radians = math.radians
np_stub.rad2deg = math.degrees
np_stub.arctan = math.atan
np_stub.sqrt = math.sqrt
np_stub.where = lambda cond, a, b: a if cond else b
np_stub.isscalar = lambda obj: isinstance(obj, int | float | complex)
sys.modules.setdefault("numpy", np_stub)

# Minimal pandas stub
pandas_stub = types.ModuleType("pandas")
sys.modules.setdefault("pandas", pandas_stub)

# Minimal pytz stub
pytz_stub = types.ModuleType("pytz")
pytz_stub.UTC = dt.UTC
sys.modules.setdefault("pytz", pytz_stub)

# Minimal dateutil parser stub
dateutil = types.ModuleType("dateutil")
parser_stub = types.ModuleType("dateutil.parser")
parser_stub.parse = lambda *a, **k: dt.datetime.now(dt.UTC)
dateutil.parser = parser_stub
sys.modules.setdefault("dateutil", dateutil)
sys.modules.setdefault("dateutil.parser", parser_stub)

# Simplify dataclass decorator


def simple_dataclass(cls=None, **kwargs):
    """Return class unchanged for dataclass stub."""

    return cls if cls is not None else (lambda c: c)

dataclasses.dataclass = simple_dataclass

# Home Assistant stubs -------------------------------------------------------
core = types.ModuleType("homeassistant.core")


class DummyStates(dict):
    """Dictionary-like container for states."""

    def get(self, entity_id):
        """Return state for ``entity_id``."""
        return super().get(entity_id)

class HomeAssistant:  # pragma: no cover - minimal stub
    """Minimal Home Assistant object."""

    def __init__(self):  # noqa: D107 - simple stub
        self.states = DummyStates()
        self.services = types.SimpleNamespace(async_call=lambda *a, **kw: None)
        self.config = types.SimpleNamespace(time_zone="UTC")

def split_entity_id(entity_id: str):
    """Split entity ID into domain and object ID."""
    return tuple(entity_id.split("."))

class Event:  # pragma: no cover - minimal stub
    """Dummy event class."""

    pass

class EventStateChangedData:  # pragma: no cover - minimal stub
    """Dummy event data class."""

    pass

class State:  # pragma: no cover - minimal stub
    """Simple representation of an entity state."""

    def __init__(self, state, attributes=None, last_updated=None):  # noqa: D107
        self.state = state
        self.attributes = attributes or {}
        self.last_updated = last_updated or dt.datetime.now(dt.UTC)

def callback(func):  # pragma: no cover - minimal stub
    """Return function unchanged (decorator stub)."""
    return func

core.HomeAssistant = HomeAssistant
core.Event = Event
core.EventStateChangedData = EventStateChangedData
core.State = State
core.callback = callback
core.split_entity_id = split_entity_id

config_entries = types.ModuleType("homeassistant.config_entries")

class ConfigEntry:  # pragma: no cover - minimal stub
    """Configuration entry container."""

    def __init__(self):  # noqa: D107 - simple stub
        self.data = {}
        self.options = {}
        self.entry_id = "test"

config_entries.ConfigEntry = ConfigEntry

const = types.ModuleType("homeassistant.const")
const.ATTR_ENTITY_ID = "entity_id"
const.SERVICE_SET_COVER_POSITION = "set_cover_position"
const.SERVICE_SET_COVER_TILT_POSITION = "set_cover_tilt_position"

util_module = types.ModuleType("homeassistant.util")
logging_module = types.ModuleType("homeassistant.util.logging")
logging_module.log_exception = lambda *a, **k: None
util_module.logging = logging_module

helpers_update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

class DataUpdateCoordinator:  # pragma: no cover - minimal stub
    """Simplified data update coordinator."""

    def __init__(self, hass, logger, name="") -> None:  # noqa: D107
        self.hass = hass
        self.logger = logger
        self.name = name
        self.config_entry = ConfigEntry()

    async def async_config_entry_first_refresh(self):
        """Return placeholder result."""
        return None

    async def async_refresh(self):  # noqa: D401 - minimal stub
        """Return placeholder result."""
        return None

    @classmethod
    def __class_getitem__(cls, item):  # pragma: no cover - support generics
        """Ignore subscription and return the class itself."""
        return cls

helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator

helpers_event = types.ModuleType("homeassistant.helpers.event")
async def async_track_point_in_time(hass, func, time):  # pragma: no cover - stub
    """Stub for ``async_track_point_in_time``."""
    return None
helpers_event.async_track_point_in_time = async_track_point_in_time

helpers_template = types.ModuleType("homeassistant.helpers.template")
def state_attr(hass, entity, attribute):  # pragma: no cover - stub
    """Retrieve attribute for entity."""
    state = hass.states.get(entity)
    if state:
        return state.attributes.get(attribute)
    return None
helpers_template.state_attr = state_attr

components_cover = types.ModuleType("homeassistant.components.cover")
components_cover.DOMAIN = "cover"

homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
homeassistant.core = core
homeassistant.util = util_module
homeassistant.config_entries = config_entries
homeassistant.const = const
homeassistant.helpers = types.ModuleType("homeassistant.helpers")
homeassistant.helpers.update_coordinator = helpers_update_coordinator
homeassistant.helpers.event = helpers_event
homeassistant.helpers.template = helpers_template
homeassistant.components = types.ModuleType("homeassistant.components")
homeassistant.components.cover = components_cover

sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.core"] = core
sys.modules["homeassistant.util"] = util_module
sys.modules["homeassistant.util.logging"] = logging_module
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.const"] = const
sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update_coordinator
sys.modules["homeassistant.helpers.event"] = helpers_event
sys.modules["homeassistant.helpers.template"] = helpers_template
sys.modules["homeassistant.components.cover"] = components_cover

# custom_components package stub --------------------------------------------
custom_components = types.ModuleType("custom_components")
simple_auto_cover = types.ModuleType("custom_components.simple_auto_cover")
custom_components.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components")]
simple_auto_cover.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/simple_auto_cover")]
custom_components.simple_auto_cover = simple_auto_cover
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.simple_auto_cover", simple_auto_cover)

# Import the coordinator module
spec = util.spec_from_file_location(
    "custom_components.simple_auto_cover.coordinator",
    Path(__file__).resolve().parents[1] / "custom_components/simple_auto_cover/coordinator.py",
)
coordinator = util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(coordinator)

AdaptiveDataUpdateCoordinator = coordinator.AdaptiveDataUpdateCoordinator
inverse_state = coordinator.inverse_state
CONF_SUNSET_POS = coordinator.CONF_SUNSET_POS
CONF_DEFAULT_HEIGHT = coordinator.CONF_DEFAULT_HEIGHT

# Helper factory -------------------------------------------------------------

def make_coordinator(cover_type="cover_blind"):
    """Create a coordinator with default options."""

    hass = HomeAssistant()
    coord = AdaptiveDataUpdateCoordinator(hass)
    coord._cover_type = cover_type
    coord.min_change = 10
    coord.time_threshold = 2
    return coord, hass

# Tests ----------------------------------------------------------------------

def test_get_current_position():
    """Return current position attribute based on cover type."""
    coord, hass = make_coordinator("cover_blind")
    hass.states["cover.test"] = State("open", {"current_position": 40})
    assert coord._get_current_position("cover.test") == 40

    coord._cover_type = "cover_tilt"
    hass.states["cover.test"] = State("open", {"current_tilt_position": 30})
    assert coord._get_current_position("cover.test") == 30


def test_check_position():
    """Verify position difference logic."""
    coord, hass = make_coordinator()
    hass.states["cover.test"] = State("open", {"current_position": 40})
    assert coord.check_position("cover.test", 50) is True
    assert coord.check_position("cover.test", 40) is False

    hass.states.pop("cover.test")
    assert coord.check_position("cover.test", 30) is False


def test_check_position_delta():
    """Ensure delta checks honor thresholds and defaults."""
    coord, hass = make_coordinator()
    hass.states["cover.test"] = State("open", {"current_position": 40})
    options = {CONF_SUNSET_POS: 0, CONF_DEFAULT_HEIGHT: 50}

    assert coord.check_position_delta("cover.test", 45, options) is False
    assert coord.check_position_delta("cover.test", 55, options) is True
    assert coord.check_position_delta("cover.test", 0, options) is True

    hass.states.pop("cover.test")
    assert coord.check_position_delta("cover.test", 30, options) is True


def test_check_time_delta():
    """Validate time delta behaviour."""
    coord, hass = make_coordinator()
    past = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=3)
    hass.states["cover.test"] = State("open", last_updated=past)
    assert coord.check_time_delta("cover.test") is True

    hass.states["cover.test"].last_updated = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1)
    assert coord.check_time_delta("cover.test") is False

    hass.states.pop("cover.test")
    assert coord.check_time_delta("cover.test") is True


def test_inverse_state():
    """Inverse a state value."""
    assert inverse_state(20) == 80

