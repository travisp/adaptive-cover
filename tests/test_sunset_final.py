"""Tests for sunset and final cover position logic."""

import datetime as dt
import types
import pytest


@pytest.fixture
def module(calculation):
    """Return the calculation module under test."""
    return calculation


def make_sundata(sunset, sunrise):
    """Create a simple sun data namespace with ``sunset`` and ``sunrise``."""
    return types.SimpleNamespace(sunset=lambda: sunset, sunrise=lambda: sunrise)


def patch_time(monkeypatch, module, new_time):
    """Patch ``datetime.utcnow`` for the calculation module."""

    class FixedDateTime(dt.datetime):
        @classmethod
        def utcnow(cls):
            return new_time

    monkeypatch.setattr(module, "datetime", FixedDateTime)


class TestVerticalCover:
    """Utility factory for ``AdaptiveVerticalCover`` instances."""

    @staticmethod
    def make_cover(module, **kwargs):
        """Construct a dummy cover using the provided ``module``."""

        class DummyCover(module.AdaptiveVerticalCover):
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
        defaults.update(kwargs)
        config_kwargs = {
            key: defaults[key]
            for key in module.CoverConfig.__dataclass_fields__
            if key in defaults
        }
        config = module.CoverConfig(**config_kwargs)
        cover = DummyCover(
            defaults["hass"],
            defaults["logger"],
            defaults["sol_azi"],
            defaults["sol_elev"],
            config,
        )
        cover.sun_data = None
        return cover


def test_sunset_valid_offset(monkeypatch, module):
    """Validate ``sunset_valid`` after the sunset offset has passed."""

    cover = TestVerticalCover.make_cover(module, sunset_off=30)
    sunset = dt.datetime(2022, 1, 1, 18, 0, tzinfo=dt.UTC)
    sunrise = dt.datetime(2022, 1, 1, 6, 0, tzinfo=dt.UTC)
    cover.sun_data = make_sundata(sunset, sunrise)

    patch_time(monkeypatch, module, dt.datetime(2022, 1, 1, 18, 20))
    assert cover.sunset_valid is False

    patch_time(monkeypatch, module, dt.datetime(2022, 1, 1, 18, 40))
    assert cover.sunset_valid is True


def test_default_after_sunset(monkeypatch, module):
    """Ensure the default position changes to ``sunset_pos`` after sunset."""

    cover = TestVerticalCover.make_cover(module, h_def=20, sunset_pos=80)
    sunset = dt.datetime(2022, 1, 1, 18, 0, tzinfo=dt.UTC)
    sunrise = dt.datetime(2022, 1, 1, 6, 0, tzinfo=dt.UTC)
    cover.sun_data = make_sundata(sunset, sunrise)

    patch_time(monkeypatch, module, dt.datetime(2022, 1, 1, 18, 5))
    assert cover.default == 80

    patch_time(monkeypatch, module, dt.datetime(2022, 1, 1, 17, 0))
    assert cover.default == 20


def test_normal_cover_state_uses_final_position(monkeypatch, module):
    """Normal cover state should apply ``sunset_pos`` after sunset."""

    cover = TestVerticalCover.make_cover(module, h_def=10, sunset_pos=75)
    sunset = dt.datetime(2022, 1, 1, 18, 0, tzinfo=dt.UTC)
    sunrise = dt.datetime(2022, 1, 1, 6, 0, tzinfo=dt.UTC)
    cover.sun_data = make_sundata(sunset, sunrise)

    patch_time(monkeypatch, module, dt.datetime(2022, 1, 1, 18, 30))
    state = module.NormalCoverState(cover)
    assert state.get_state() == 75
