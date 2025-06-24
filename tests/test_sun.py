"""Tests for solar calculations in :mod:`sun`."""

from __future__ import annotations

import types
import datetime as dt

import custom_components.simple_auto_cover.sun as sun


def test_solar_azimuth_and_elevation(monkeypatch):
    """Verify solar azimuth and elevation results for ``SunData``."""
    times = [
        dt.datetime(2025, 1, 1, 0, 0) + dt.timedelta(minutes=5 * i) for i in range(3)
    ]

    az_calls = []
    el_calls = []

    class DummyLocation:
        def solar_azimuth(self, time, elevation):
            az_calls.append((time, elevation))
            return time.minute + elevation

        def solar_elevation(self, time, elevation):
            el_calls.append((time, elevation))
            return time.minute - elevation

    def dummy_get_astral_location(hass):
        return DummyLocation(), 5

    monkeypatch.setattr(sun, "get_astral_location", dummy_get_astral_location)
    monkeypatch.setattr(sun.SunData, "times", property(lambda self: times))

    sun_data = sun.SunData("UTC", types.SimpleNamespace())

    assert sun_data.solar_azimuth == [t.minute + 5 for t in times]
    assert sun_data.solar_elevation == [t.minute - 5 for t in times]
    assert az_calls == [(t, 5) for t in times]
    assert el_calls == [(t, 5) for t in times]


def test_times_range(monkeypatch):
    """Ensure times covers a full day in 5 minute increments."""

    def dummy_get_astral_location(hass):
        return types.SimpleNamespace(), 0

    monkeypatch.setattr(sun, "get_astral_location", dummy_get_astral_location)

    sun_data = sun.SunData("UTC", types.SimpleNamespace())
    times = sun_data.times

    assert len(times) == 289
    assert times[0].minute == 0 and times[0].hour == 0
    assert times[-1] - times[0] == dt.timedelta(days=1)
    assert all(t.tzinfo is not None for t in times)


def test_times_are_five_minute_steps(monkeypatch):
    """Verify consecutive times differ by exactly five minutes."""

    def dummy_get_astral_location(hass):
        return types.SimpleNamespace(), 0

    monkeypatch.setattr(sun, "get_astral_location", dummy_get_astral_location)

    sun_data = sun.SunData("UTC", types.SimpleNamespace())
    times = sun_data.times

    deltas = [b - a for a, b in zip(times, times[1:])]
    assert all(delta == dt.timedelta(minutes=5) for delta in deltas)


def test_timezone_is_zoneinfo(monkeypatch):
    """Ensure timezone is stored as a ``ZoneInfo`` instance."""

    def dummy_get_astral_location(hass):
        return types.SimpleNamespace(), 0

    monkeypatch.setattr(sun, "get_astral_location", dummy_get_astral_location)

    sun_data = sun.SunData("UTC", types.SimpleNamespace())

    from zoneinfo import ZoneInfo

    assert isinstance(sun_data.timezone, ZoneInfo)
    assert sun_data.timezone.key == "UTC"
