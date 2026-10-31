"""
core/watcher.py
---------------
AlarmWatcher — daemon thread that polls every second and fires due alarms.
No UI logic here; it calls a callback supplied by the entry point.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from core.store import AlarmStore
from models.alarm import Alarm

# Seconds between each poll cycle — 1 s gives ±1 s precision
POLL_INTERVAL: float = 1.0


class AlarmWatcher:
    """
    Runs a single daemon thread that wakes every POLL_INTERVAL seconds,
    checks all active alarms, and invokes *on_fire* for each due alarm.

    Parameters
    ----------
    store : AlarmStore
        The shared alarm store to poll.
    on_fire : Callable[[Alarm], None]
        Callback invoked (on the watcher thread) when an alarm is due.
        Keep this callback fast and non-blocking; spawn a thread if needed.
    """

    def __init__(
        self,
        store: AlarmStore,
        on_fire: Callable[[Alarm], None],
    ) -> None:
        self._store    = store
        self._on_fire  = on_fire
        self._stop     = threading.Event()
        self._thread: threading.Thread | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background watcher thread (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="AlarmWatcher",
            daemon=True,   # dies automatically when main thread exits
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the watcher to stop and wait up to 2 s for it to finish."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    # ── Core loop ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Poll the store every POLL_INTERVAL seconds for due alarms."""
        while not self._stop.wait(timeout=POLL_INTERVAL):
            now = time.time()
            for alarm in self._store.list_all():
                # Gate: only `active` matters here.
                # `fired` is historical metadata — a snoozed alarm has
                # fired=True but active=True and must still re-fire.
                if alarm.active and now >= alarm.timestamp:
                    # Mark fired BEFORE calling the callback so re-entrant
                    # polls don't double-fire on slow callbacks.
                    self._store.mark_fired(alarm.id)
                    try:
                        self._on_fire(alarm)
                    except Exception:
                        pass  # Never let a bad callback kill the watcher
