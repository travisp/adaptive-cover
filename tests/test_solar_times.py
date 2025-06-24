"""Tests for AdaptiveGeneralCover.solar_times."""

from __future__ import annotations

import types
import datetime as dt

import custom_components.simple_auto_cover.calculation as calculation


def test_solar_times_returns_first_and_last_valid(monkeypatch):
    """Validate filtering of times based on azimuth and elevation."""

    base = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
    times = [base + dt.timedelta(minutes=5 * i) for i in range(5)]
    azimuths = [60, 80, 90, 100, 120]
    elevations = [-1, 10, 20, 20, -1]

    sun_data = types.SimpleNamespace(
        times=times, solar_azimuth=azimuths, solar_elevation=elevations
    )

    class DummyCover(calculation.AdaptiveGeneralCover):
        __test__ = False

        def __post_init__(self):
            self.sun_data = sun_data

        def calculate_position(self) -> float:
            return 0.0

        def calculate_percentage(self) -> int:
            return 0

    config = calculation.CoverConfig(
        sunset_pos=0,
        sunset_off=0,
        sunrise_off=0,
        timezone="UTC",
        fov_left=20,
        fov_right=20,
        win_azi=90,
        h_def=0,
        max_pos=100,
        min_pos=0,
        max_pos_bool=False,
        min_pos_bool=False,
        blind_spot_left=None,
        blind_spot_right=None,
        blind_spot_elevation=None,
        blind_spot_on=False,
        min_elevation=None,
        max_elevation=None,
    )

    cover = DummyCover(
        hass=None,
        logger=types.SimpleNamespace(debug=lambda *a, **k: None),
        sol_azi=0,
        sol_elev=0,
        config=config,
    )

    start, end = cover.solar_times()

    assert start == times[1]
    assert end == times[3]
