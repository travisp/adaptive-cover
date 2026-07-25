"""Tests for external override state normalization."""

import pytest
from homeassistant.core import State

from custom_components.simple_auto_cover.override import (
    OverrideMode,
    parse_external_override,
)


@pytest.mark.parametrize(
    ("raw_state", "attributes", "mode", "target", "force"),
    [
        ("auto", {"reason": "clear"}, OverrideMode.AUTO, None, False),
        ("hold", {}, OverrideMode.HOLD, None, False),
        ("42", {}, OverrideMode.POSITION, 42, False),
        ("42.5", {"force": True}, OverrideMode.POSITION, 43, True),
        ("42", {"force": "true"}, OverrideMode.POSITION, 42, False),
        ("101", {}, OverrideMode.INVALID, None, False),
        ("AUTO", {}, OverrideMode.INVALID, None, False),
        ("not-a-position", {}, OverrideMode.INVALID, None, False),
    ],
)
def test_parse_external_override(raw_state, attributes, mode, target, force):
    """Normalize supported and invalid override entity states."""
    override = parse_external_override(State("sensor.override", raw_state, attributes))

    assert override.mode is mode
    assert override.target == target
    assert override.force is force


def test_parse_external_override_unavailable():
    """Treat missing and unavailable override entities as a safe hold."""
    assert parse_external_override(None).holds_commands is True
    state = State("sensor.override", "unavailable")
    assert parse_external_override(state).holds_commands is True
