"""
alarm_clock.py
--------------
Entry point — wires all modules together and owns the application lifecycle.

Usage
-----
    python alarm_clock.py

Architecture
------------
    alarm_clock.py          ← you are here (lifecycle + wiring)
    models/alarm.py         ← Alarm dataclass (pure data)
    core/store.py           ← AlarmStore (CRUD + persistence)
    core/watcher.py         ← AlarmWatcher (background daemon thread)
    ui/display.py           ← All terminal rendering
    ui/repl.py              ← Interactive command loop
    utils/sound.py          ← Cross-platform sound alert
"""

from __future__ import annotations

import signal
import sys
import io
import threading

# ── UTF-8 stdout on Windows (must happen before any other import that prints) ──
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.store   import AlarmStore
from core.watcher import AlarmWatcher
from models.alarm import Alarm
from ui           import display as D
from ui           import repl
from utils        import sound


# ── Fire callback (called on the watcher thread) ──────────────────────────

def _on_alarm_fire(alarm: Alarm) -> None:
    """
    Invoked by AlarmWatcher when an alarm is due.
    Runs in a short-lived thread so the watcher loop is never blocked.
    """
    def _notify():
        sound.play_alert()
        D.print_fire_alert(alarm)

    threading.Thread(target=_notify, daemon=True, name=f"Alert-{alarm.id}").start()


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    # Graceful Ctrl+C: let the REPL's except clause handle shutdown cleanly
    def _sigint(sig, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _sigint)

    # Print welcome banner
    D.print_banner()
    D.print_info("Tip: 'set 60 Meeting reminder'  fires after 60 seconds.")

    # Bootstrap store (loads persisted alarms from disk)
    store   = AlarmStore()
    loaded  = store.list_all()
    if loaded:
        D.print_info(f"Loaded {len(loaded)} alarm(s) from disk.")

    # Start background watcher
    watcher = AlarmWatcher(store=store, on_fire=_on_alarm_fire)
    watcher.start()

    # Run interactive REPL (blocks until user quits)
    try:
        repl.run(store)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        print(f"\n{D.CYAN}  👋  Goodbye! Alarm clock stopped.{D.RESET}\n")


if __name__ == "__main__":
    main()
