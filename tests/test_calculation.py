"""Tests for calculation helpers."""

from __future__ import annotations

import sys
import types
import math
from pathlib import Path
from importlib import util
import pytest

np_stub = types.ModuleType("numpy")
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

pandas_stub = types.ModuleType("pandas")
sys.modules.setdefault("pandas", pandas_stub)

homeassistant = types.ModuleType("homeassistant")
core = types.ModuleType("homeassistant.core")


class HomeAssistant:  # pragma: no cover - minimal stub
    """Stub for Home Assistant object used in tests."""

    pass


core.HomeAssistant = HomeAssistant
homeassistant.core = core
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.core", core)

custom_components = types.ModuleType("custom_components")
simple_auto_cover = types.ModuleType("custom_components.simple_auto_cover")
custom_components.simple_auto_cover = simple_auto_cover
custom_components.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components")
]
simple_auto_cover.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components/simple_auto_cover")
]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.simple_auto_cover", simple_auto_cover)

sun_stub = types.ModuleType("custom_components.simple_auto_cover.sun")


class SunData:  # pragma: no cover - minimal stub
    """Stub for SunData class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize SunData stub."""
        pass


sun_stub.SunData = SunData
sys.modules.setdefault("custom_components.simple_auto_cover.sun", sun_stub)

spec = util.spec_from_file_location(
    "custom_components.simple_auto_cover.calculation",
    Path(__file__).resolve().parents[1]
    / "custom_components/simple_auto_cover/calculation.py",
)
calc = util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(calc)

AdaptiveVerticalCover = calc.AdaptiveVerticalCover
NormalCoverState = calc.NormalCoverState


class TestVerticalCover(AdaptiveVerticalCover):
    """Vertical cover that skips sun data setup."""

    def __post_init__(self):
        """Avoid SunData initialization during tests."""
        pass

    __test__ = False


def make_cover(**kwargs):
    """Create a ``TestVerticalCover`` instance with defaults."""

    defaults = {
        "hass": None,
        "sol_azi": 0,
        "sol_elev": 45,
        "sunset_pos": 0,
        "sunset_off": 0,
        "sunrise_off": 0,
        "timezone": "UTC",
        "fov_left": 90,
        "fov_right": 90,
        "win_azi": 0,
        "h_def": 0,
        "max_pos": 100,
        "min_pos": 0,
        "max_pos_bool": False,
        "min_pos_bool": False,
        "blind_spot_left": None,
        "blind_spot_right": None,
        "blind_spot_elevation": None,
        "blind_spot_on": False,
        "min_elevation": None,
        "max_elevation": None,
        "distance": 1,
        "h_win": 2,
    }
    defaults.update(kwargs)
    cover = TestVerticalCover(**defaults)
    cover.sun_data = None
    return cover


def test_vertical_cover_calculation():
    """Verify basic position and percentage calculations."""
    cover = make_cover()
    assert cover.calculate_position() == pytest.approx(1)
    assert cover.calculate_percentage() == 50


def test_normal_cover_state_default():
    """Ensure default value is used when sun is not valid."""
    class DummyCover:
        def __init__(self):
            self.direct_sun_valid = False
            self.default = 30
            self.apply_max_position = False
            self.apply_min_position = False
            self.max_pos = 100
            self.min_pos = 0

        def calculate_percentage(self):
            return 80

    state = NormalCoverState(DummyCover())
    assert state.get_state() == 30


def test_normal_cover_state_apply_max():
    """Ensure max position is respected when exceeded."""
    class DummyCover:
        def __init__(self):
            self.direct_sun_valid = True
            self.default = 0
            self.apply_max_position = True
            self.max_pos = 50
            self.apply_min_position = False
            self.min_pos = 0

        def calculate_percentage(self):
            return 80

    state = NormalCoverState(DummyCover())
    assert state.get_state() == 50

