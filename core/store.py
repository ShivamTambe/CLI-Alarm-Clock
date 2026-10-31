"""
core/store.py
-------------
AlarmStore — thread-safe CRUD operations and JSON persistence.
No UI, no sound, no threading here.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable, List, Optional

from models.alarm import Alarm

# Default file sits next to the project root (one level up from core/)
_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "alarms.json",
)


class AlarmStore:
    """
    Manages a collection of Alarm objects.

    Responsibilities
    ----------------
    - Add / get / delete / list / clear alarms
    - Load from and atomically save to a JSON file
    - Thread-safe via a single RLock (reentrant to allow nested calls)
    """

    def __init__(self, persistence_path: str = _DEFAULT_PATH) -> None:
        self._path   = persistence_path
        self._lock   = threading.RLock()
        self._alarms: List[Alarm] = []
        self._load()

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load alarms from disk; silently starts fresh if file is absent/corrupt."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                raw: List[dict] = json.load(fh)
            with self._lock:
                self._alarms = [Alarm.from_dict(d) for d in raw]
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupt file — start fresh rather than crashing
            self._alarms = []

    def save(self) -> None:
        """Atomically write current alarms to disk (write-then-rename)."""
        tmp = self._path + ".tmp"
        with self._lock:
            data = [a.to_dict() for a in self._alarms]
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            os.replace(tmp, self._path)
        except OSError:
            pass  # Caller (watcher/repl) may handle or ignore

    # ── CRUD ───────────────────────────────────────────────────────────────

    def add(self, delay_seconds: float, label: str) -> Alarm:
        """
        Create and store a new alarm that fires *delay_seconds* from now.

        Parameters
        ----------
        delay_seconds : float
            How many seconds from the current moment until the alarm fires.
        label : str
            Human-readable name for the alarm.

        Returns
        -------
        Alarm
            The newly created alarm (already persisted to disk).
        """
        alarm = Alarm(
            timestamp=time.time() + delay_seconds,
            label=label or "Alarm",
        )
        with self._lock:
            self._alarms.append(alarm)
        self.save()
        return alarm

    def get(self, alarm_id: str) -> Optional[Alarm]:
        """Return the first alarm whose id starts with *alarm_id*, or None."""
        with self._lock:
            for a in self._alarms:
                if a.id.startswith(alarm_id):
                    return a
        return None

    def delete(self, alarm_id: str) -> bool:
        """
        Remove alarm by ID prefix.

        Returns
        -------
        bool
            True if an alarm was found and removed, False otherwise.
        """
        with self._lock:
            before = len(self._alarms)
            self._alarms = [a for a in self._alarms if not a.id.startswith(alarm_id)]
            removed = len(self._alarms) < before
        if removed:
            self.save()
        return removed

    def list_all(self) -> List[Alarm]:
        """Return a shallow copy of all alarms (safe to iterate outside the lock)."""
        with self._lock:
            return list(self._alarms)

    def clear(self) -> None:
        """Remove all alarms."""
        with self._lock:
            self._alarms.clear()
        self.save()

    def snooze(self, alarm_id: str, extra_seconds: float) -> bool:
        """
        Reschedule a fired alarm by adding *extra_seconds* to its timestamp.

        Returns
        -------
        bool
            True if the alarm was found and updated.
        """
        with self._lock:
            alarm = self.get(alarm_id)
            if alarm is None:
                return False
            # Re-anchor from now so snooze always means "N seconds from this moment"
            alarm.timestamp = time.time() + extra_seconds
            alarm.active    = True
            alarm.fired     = True   # remains True — it has fired before
        self.save()
        return True

    def dismiss(self, alarm_id: str) -> bool:
        """
        Mark an alarm as dismissed (active=False).

        Returns
        -------
        bool
            True if found and updated.
        """
        with self._lock:
            alarm = self.get(alarm_id)
            if alarm is None:
                return False
            alarm.active = False
            alarm.fired  = True
        self.save()
        return True

    def mark_fired(self, alarm_id: str) -> None:
        """Internal: called by the watcher when an alarm's time has come."""
        with self._lock:
            alarm = self.get(alarm_id)
            if alarm:
                alarm.fired  = True
                alarm.active = False   # auto-dismiss; user can snooze to re-activate
        self.save()
