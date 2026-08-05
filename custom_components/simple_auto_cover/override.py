"""Normalize external override entity states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

ATTR_FORCE = "force"
ATTR_REASON = "reason"


class OverrideMode(StrEnum):
    """Supported states for an external override entity."""

    AUTO = "auto"
    HOLD = "hold"
    POSITION = "position"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True)
class ExternalOverride:
    """Normalized state read from the configured external override entity."""

    mode: OverrideMode
    target: int | None = None
    force: bool = False
    reason: str | None = None
    raw_state: str | None = None

    @property
    def holds_commands(self) -> bool:
        """Return whether this state prevents automatic cover commands."""
        return self.mode in {
            OverrideMode.HOLD,
            OverrideMode.UNAVAILABLE,
            OverrideMode.INVALID,
        }


def parse_external_override(state: State | None) -> ExternalOverride:
    """Normalize a Home Assistant state into an external override."""
    if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
        return ExternalOverride(
            mode=OverrideMode.UNAVAILABLE,
            raw_state=state.state if state else None,
        )

    raw_state = state.state
    reason_value = state.attributes.get(ATTR_REASON)
    reason = str(reason_value) if reason_value is not None else None

    if raw_state == OverrideMode.AUTO:
        return ExternalOverride(
            mode=OverrideMode.AUTO,
            reason=reason,
            raw_state=state.state,
        )
    if raw_state == OverrideMode.HOLD:
        return ExternalOverride(
            mode=OverrideMode.HOLD,
            reason=reason,
            raw_state=state.state,
        )

    try:
        numeric_state = float(raw_state)
    except ValueError:
        return ExternalOverride(
            mode=OverrideMode.INVALID,
            reason=reason,
            raw_state=state.state,
        )

    if not 0 <= numeric_state <= 100:
        return ExternalOverride(
            mode=OverrideMode.INVALID,
            reason=reason,
            raw_state=state.state,
        )

    return ExternalOverride(
        mode=OverrideMode.POSITION,
        target=int(numeric_state + 0.5),
        force=state.attributes.get(ATTR_FORCE) is True,
        reason=reason,
        raw_state=state.state,
    )
