"""Manage manual control state for covers."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from homeassistant.util import dt as dt_util

from .const import SensorType


class ManualOverrideManager:
    """Track per-cover manual control state."""

    def __init__(
        self,
        reset_duration: dict[str, int],
        logger,
        on_change: Callable[[str], None],
    ) -> None:
        """Initialize the manual control manager."""
        self.manual_control_time: dict[str, dt.datetime] = {}
        self.reset_duration = dt.timedelta(**reset_duration)
        self.logger = logger
        self._on_change = on_change

    def handle_state_change(
        self,
        event,
        expected_position,
        cover_type,
        reset_timer,
        manual_threshold,
    ) -> None:
        """Mark a cover as manual when its reported movement was not expected."""
        position_attribute = (
            "current_tilt_position"
            if cover_type == SensorType.TILT
            else "current_position"
        )
        old_position = event.old_state.attributes.get(position_attribute)
        new_position = event.new_state.attributes.get(position_attribute)
        finished_moving = event.old_state.state in ["opening", "closing"] and (
            event.new_state.state not in ["opening", "closing"]
        )
        if old_position == new_position and not finished_moving:
            return
        if new_position == expected_position:
            return
        if (
            manual_threshold is not None
            and abs(expected_position - new_position) < manual_threshold
        ):
            self.logger.debug(
                "Position change is less than threshold %s for %s",
                manual_threshold,
                event.entity_id,
            )
            return

        self.logger.debug(
            "Manual change detected for %s. Our state: %s, new state: %s",
            event.entity_id,
            expected_position,
            new_position,
        )
        self.mark_manual_control(event.entity_id, reset_timer)

    def mark_manual_control(self, entity_id: str, reset_timer: bool) -> None:
        """Mark a cover as manual and start or refresh its reset timer."""
        if entity_id in self.manual_control_time and not reset_timer:
            return

        self.manual_control_time[entity_id] = dt_util.utcnow()
        self.logger.debug(
            "Manual control for %s expires after %s seconds",
            entity_id,
            self.reset_duration.total_seconds(),
        )
        self._on_change(entity_id)

    def restore(self, entity_id: str, expires_at: dt.datetime) -> None:
        """Restore manual control with its original absolute expiry."""
        self.manual_control_time[entity_id] = expires_at - self.reset_duration

    def reset_if_needed(self) -> list[str]:
        """Reset and return covers whose manual control has expired."""
        now = dt_util.utcnow()
        expired = [
            entity_id
            for entity_id, started_at in self.manual_control_time.items()
            if now >= started_at + self.reset_duration
        ]
        for entity_id in expired:
            self.logger.debug(
                "Resetting manual override for %s, because duration has elapsed",
                entity_id,
            )
            self.reset(entity_id)
        return expired

    def reset(self, entity_id: str) -> None:
        """Reset manual control for a cover."""
        del self.manual_control_time[entity_id]
        self.logger.debug("Reset manual override for %s", entity_id)
        self._on_change(entity_id)

    def is_cover_manual(self, entity_id: str) -> bool:
        """Check if a cover is under manual control."""
        return entity_id in self.manual_control_time

    def expires_at(self, entity_id: str) -> dt.datetime:
        """Return when manual control expires for a cover."""
        return self.manual_control_time[entity_id] + self.reset_duration

    @property
    def binary_cover_manual(self) -> bool:
        """Check if any cover is under manual control."""
        return bool(self.manual_control_time)

    @property
    def manual_controlled(self) -> list[str]:
        """Get the list of covers under manual control."""
        return sorted(self.manual_control_time)
