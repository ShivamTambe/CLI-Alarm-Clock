"""
models/alarm.py
---------------
Alarm dataclass — pure data, zero side-effects.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Alarm:
    """
    Represents a single alarm.

    Fields
    ------
    timestamp : float
        Unix epoch (seconds) at or after which the alarm should fire.
        Computed as ``time.time() + delay_seconds`` when the alarm is created.
    label : str
        Human-readable description (e.g. "Coffee break").
    id : str
        8-character prefix of a UUID4 — unique within a session.
    active : bool
        True  → alarm is pending or snoozed (still wants to fire).
        False → alarm has been dismissed or manually cancelled.
    fired : bool
        True  → alarm has been triggered at least once.
        False → alarm has never fired.

    State matrix
    ------------
    active=True,  fired=False → PENDING   (waiting to fire for the first time)
    active=True,  fired=True  → SNOOZED   (fired, rescheduled)
    active=False, fired=True  → DISMISSED (done)
    active=False, fired=False → CANCELLED (deleted before firing)
    """

    timestamp: float
    label: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    active: bool = True
    fired: bool = False

    # ── Derived helpers ────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        """Return a human-readable state label."""
        if self.active and not self.fired:
            return "pending"
        if self.active and self.fired:
            return "snoozed"
        if not self.active and self.fired:
            return "dismissed"
        return "cancelled"

    @property
    def seconds_remaining(self) -> float:
        """Seconds until the alarm fires (negative if overdue)."""
        return self.timestamp - time.time()

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to a plain dict suitable for JSON serialisation."""
        return {
            "id":        self.id,
            "timestamp": self.timestamp,
            "label":     self.label,
            "active":    self.active,
            "fired":     self.fired,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        """Reconstruct an Alarm from a deserialised JSON dict."""
        return cls(
            id=        data["id"],
            timestamp= float(data["timestamp"]),
            label=     data["label"],
            active=    bool(data["active"]),
            fired=     bool(data["fired"]),
        )
