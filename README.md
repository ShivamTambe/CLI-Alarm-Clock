# ⏰ CLI Alarm Clock

A lightweight, modular command-line alarm clock written in pure Python.  
Set alarms in **seconds from now**, get audible + visual alerts, snooze, dismiss, and persist alarms across sessions — zero third-party dependencies required.

---

## Features

- ⏱ Set alarms using **seconds from now** (e.g. `set 300 Coffee break`)
- 🔔 **Audible alert** when an alarm fires (`winsound` on Windows, `afplay` on macOS, `aplay` on Linux, terminal bell fallback)
- 📋 **List** all alarms with live countdowns and color-coded states
- 💤 **Snooze** a fired alarm by any number of seconds
- ✅ **Dismiss** a fired alarm permanently
- 💾 **Persistence** — alarms survive restarts via `alarms.json`
- 🧵 **Thread-safe** background watcher (daemon thread, polls every second)
- 🎨 Colored ANSI terminal output (Windows 10+, macOS, Linux)

---

## Requirements

- Python **3.10+** (uses `match`-free code; tested on 3.13)
- No pip installs required — stdlib only
- Optional: `pip install colorama` for enhanced color support on older Windows terminals

---

## Quick Start

```bash
# Clone or navigate to the project folder
cd Alarm_Clock

# Run
python alarm_clock.py
```

---

## Commands

| Command | Example | Description |
|---------|---------|-------------|
| `set <seconds> [label]` | `set 300 Coffee break` | Set alarm N seconds from now |
| `list` | `list` | Show all alarms with countdown and state |
| `del <id>` | `del a1b2c3d4` | Delete an alarm by ID |
| `snooze <id> [seconds]` | `snooze a1b2c3d4 60` | Snooze a fired alarm (default: 300 s) |
| `dismiss <id>` | `dismiss a1b2c3d4` | Dismiss a fired alarm permanently |
| `clear` | `clear` | Remove all alarms |
| `help` | `help` | Show the command menu |
| `quit` | `quit` | Exit the alarm clock |

> **Tip:** You can use `ls`, `rm`, `delete` and `exit` / `q` as aliases too.

---

## Usage Walkthrough

```
> set 60 Stand up reminder
  ✓  Alarm [a1b2c3d4] 'Stand up reminder' will fire in 60s  (at 11:30:00)

> list
  ID        FIRES AT                COUNTDOWN     STATE       LABEL
  ────────────────────────────────────────────────────────────────────
  a1b2c3d4  11:30:00  31 Oct 2026   58s           pending     Stand up reminder

# ... 60 seconds later ...

  ╔══════════════════════════════════════════════╗
  ║  🔔  ALARM FIRED!                           ║
  ║  ⏱  Scheduled : 11:30:00  31 Oct 2026       ║
  ║  📝  Label     : Stand up reminder           ║
  ║  🆔  ID        : a1b2c3d4                    ║
  ╠══════════════════════════════════════════════╣
  ║  snooze a1b2c3d4 [secs]   dismiss a1b2c3d4  ║
  ╚══════════════════════════════════════════════╝

> snooze a1b2c3d4 120
  ✓  Alarm 'a1b2c3d4' snoozed for 120 s.

# ... 120 seconds later — fires again with sound and alert ...

> dismiss a1b2c3d4
  ✓  Alarm 'a1b2c3d4' dismissed.
```

---

## Alarm States

| State | Meaning |
|-------|---------|
| `pending` | Waiting to fire for the first time |
| `snoozed` | Fired at least once, rescheduled via snooze |
| `dismissed` | Done — will not fire again |
| `cancelled` | Deleted by the user before firing |

---

## Project Structure

```
Alarm_Clock/
│
├── alarm_clock.py        # Entry point — wires all modules, owns lifecycle
│
├── models/
│   └── alarm.py          # Alarm dataclass (pure data, no side-effects)
│
├── core/
│   ├── store.py          # AlarmStore — thread-safe CRUD + JSON persistence
│   └── watcher.py        # AlarmWatcher — daemon thread, fires due alarms
│
├── ui/
│   ├── display.py        # All terminal rendering (colors, table, alert box)
│   └── repl.py           # Interactive command loop
│
├── utils/
│   └── sound.py          # Cross-platform audio alert
│
├── tests/
│   └── test_core.py      # Synchronous unit tests (38 cases)
│
└── alarms.json           # Auto-created persistence file (add to .gitignore)
```

### Module responsibilities

| Module | Does | Does NOT |
|--------|------|----------|
| `models/alarm.py` | Shape of data, serialisation | Any logic or I/O |
| `core/store.py` | CRUD, load/save JSON | UI, sound, threading |
| `core/watcher.py` | Poll + fire callback | Know about sound or display |
| `ui/display.py` | Print everything | Business logic |
| `ui/repl.py` | Parse commands, call store | Direct I/O beyond input/print |
| `utils/sound.py` | Play beep | Know about alarms |
| `alarm_clock.py` | Wire-up, lifecycle | Business logic |

---

## Running the Tests

```bash
python tests/test_core.py
```

Tests cover the `Alarm` dataclass and all `AlarmStore` methods synchronously — no background threads are started.

```
==================================================
  alarm_clock — unit tests
==================================================

[1] Alarm dataclass        8 PASS
[2] Alarm serialisation    6 PASS
[3] AlarmStore.add         5 PASS
[4] AlarmStore.get         3 PASS
[5] AlarmStore.delete      3 PASS
[6] AlarmStore.snooze      5 PASS
[7] AlarmStore.dismiss     4 PASS
[8] AlarmStore.mark_fired  2 PASS
[9] JSON persistence       4 PASS
[10] AlarmStore.clear      1 PASS

  All tests passed!
==================================================
```

---

## How It Works

```
alarm_clock.py
    │
    ├─► AlarmStore      loads alarms.json on startup
    │       │
    │       └─► Alarm   dataclass with timestamp (Unix float),
    │                   label, id, active, fired
    │
    ├─► AlarmWatcher    daemon thread, polls every 1 second
    │       │
    │       └─► if alarm.active and time.time() >= alarm.timestamp:
    │               store.mark_fired(id)    ← sets active=False
    │               on_fire(alarm)          ← callback
    │                   │
    │                   ├─► sound.play_alert()
    │                   └─► display.print_fire_alert()
    │
    └─► repl.run()      blocks on input(), dispatches commands
```

**Key design decisions:**

- **Seconds-from-now input** → stored as a Unix float (`time.time() + N`). Comparison, snooze, and serialisation are all trivial arithmetic.
- **`active` is the only watcher gate.** `fired` is history metadata only — a snoozed alarm has `fired=True` but `active=True` and must re-fire.
- **`Event.wait(timeout)`** instead of `time.sleep()` — `stop()` responds in ≤1 s.
- **Atomic JSON write** (write to `.tmp` → `os.replace`) — no corrupt file on crash.
- **`mark_fired` before callback** — prevents double-firing if the callback is slow.

---

## .gitignore

Add this to a `.gitignore` to avoid committing session data:

```
alarms.json
alarms.json.tmp
__pycache__/
*.pyc
```
