"""Tests for calculation helpers."""

from __future__ import annotations

import types
import pytest


@pytest.fixture
def module(calculation):
    """Return the calculation module under test."""
    return calculation


class TestVerticalCover:
    """Helper class for AdaptiveVerticalCover test instances."""

    @staticmethod
    def make_cover(calculation_module, **kwargs):
        """Create a dummy ``AdaptiveVerticalCover`` instance."""

        class DummyCover(calculation_module.AdaptiveVerticalCover):
            __test__ = False

            def __post_init__(self):
                pass

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
            "logger": types.SimpleNamespace(debug=lambda *a, **k: None),
        }
        if (
            hasattr(
                calculation_module.AdaptiveVerticalCover,
                "__dataclass_fields__",
            )
            and "logger"
            in calculation_module.AdaptiveVerticalCover.__dataclass_fields__
        ):
            defaults.setdefault(
                "logger", types.SimpleNamespace(debug=lambda *a, **k: None)
            )
        defaults.update(kwargs)
        cover = DummyCover(**defaults)
        cover.sun_data = None
        return cover


def test_vertical_cover_calculation(module):
    """Test calculation of the adaptive vertical cover."""
    cover = TestVerticalCover.make_cover(module)
    assert cover.calculate_position() == pytest.approx(1)
    assert cover.calculate_percentage() == 50


def test_normal_cover_state_default(module):
    """Test the default state when no max position is applied."""

    class DummyCover:
        def __init__(self):
            self.direct_sun_valid = False
            self.default = 30
            self.apply_max_position = False
            self.apply_min_position = False
            self.max_pos = 100
            self.min_pos = 0
            self.logger = types.SimpleNamespace(debug=lambda *a, **k: None)

        def calculate_percentage(self):
            return 80

    state = module.NormalCoverState(DummyCover())
    assert state.get_state() == 30


def test_normal_cover_state_apply_max(module):
    """Test the state when the max position should be applied."""

    class DummyCover:
        def __init__(self):
            self.direct_sun_valid = True
            self.default = 0
            self.apply_max_position = True
            self.max_pos = 50
            self.apply_min_position = False
            self.min_pos = 0
            self.logger = types.SimpleNamespace(debug=lambda *a, **k: None)

        def calculate_percentage(self):
            return 80

    state = module.NormalCoverState(DummyCover())
    assert state.get_state() == 50
