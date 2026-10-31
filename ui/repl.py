"""
ui/repl.py
----------
Interactive command-line REPL.
Parses user input and delegates to AlarmStore — no direct IO or alarm logic.
"""

from __future__ import annotations

from core.store import AlarmStore
from ui import display as D

DEFAULT_SNOOZE_SECONDS: float = 300.0   # 5 minutes


def run(store: AlarmStore) -> None:
    """
    Block until the user types 'quit' or sends EOF/Ctrl+C.

    Parameters
    ----------
    store : AlarmStore
        The shared store; all reads/writes go through it.
    """
    D.print_menu()

    while True:
        try:
            raw = input(f"{D.YELLOW}  > {D.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd   = parts[0].lower()
        rest  = parts[1].strip() if len(parts) > 1 else ""

        # ── set ────────────────────────────────────────────────────────────
        if cmd == "set":
            _cmd_set(store, rest)

        # ── list ───────────────────────────────────────────────────────────
        elif cmd in ("list", "ls"):
            D.print_alarm_table(store.list_all())

        # ── del ────────────────────────────────────────────────────────────
        elif cmd in ("del", "delete", "rm"):
            _cmd_del(store, rest)

        # ── snooze ─────────────────────────────────────────────────────────
        elif cmd == "snooze":
            _cmd_snooze(store, rest)

        # ── dismiss ────────────────────────────────────────────────────────
        elif cmd == "dismiss":
            _cmd_dismiss(store, rest)

        # ── clear ──────────────────────────────────────────────────────────
        elif cmd == "clear":
            store.clear()
            D.print_success("All alarms cleared.")

        # ── help ───────────────────────────────────────────────────────────
        elif cmd in ("help", "h", "?"):
            D.print_menu()

        # ── quit ───────────────────────────────────────────────────────────
        elif cmd in ("quit", "exit", "q"):
            break

        else:
            D.print_error(f"Unknown command '{cmd}'. Type 'help' for options.")


# ── Command handlers ───────────────────────────────────────────────────────

def _cmd_set(store: AlarmStore, args: str) -> None:
    """Parse 'set <seconds> [label]' and add alarm."""
    if not args:
        D.print_error("Usage:  set <seconds> [label]   e.g.  set 300 Coffee")
        return

    tokens = args.split(maxsplit=1)
    try:
        delay = float(tokens[0])
    except ValueError:
        D.print_error(f"'{tokens[0]}' is not a valid number of seconds.")
        return

    if delay <= 0:
        D.print_error("Seconds must be a positive number.")
        return

    label = tokens[1] if len(tokens) > 1 else ""
    alarm = store.add(delay, label)

    # Human-friendly confirmation
    import datetime
    fires_at = datetime.datetime.fromtimestamp(alarm.timestamp).strftime("%H:%M:%S")
    D.print_success(
        f"Alarm [{alarm.id}] '{alarm.label}' will fire in "
        f"{int(delay)}s  (at {fires_at})"
    )


def _cmd_del(store: AlarmStore, args: str) -> None:
    if not args:
        D.print_error("Usage:  del <id>")
        return
    if store.delete(args):
        D.print_success(f"Alarm '{args}' deleted.")
    else:
        D.print_error(f"No alarm found with ID '{args}'.")


def _cmd_snooze(store: AlarmStore, args: str) -> None:
    tokens = args.split()
    if not tokens:
        D.print_error("Usage:  snooze <id> [seconds]   (default: 300 s)")
        return

    aid = tokens[0]
    seconds = DEFAULT_SNOOZE_SECONDS
    if len(tokens) > 1:
        try:
            seconds = float(tokens[1])
        except ValueError:
            D.print_error(f"'{tokens[1]}' is not a valid number of seconds.")
            return

    if store.snooze(aid, seconds):
        D.print_success(f"Alarm '{aid}' snoozed for {int(seconds)} s.")
    else:
        D.print_error(f"No alarm found with ID '{aid}'.")


def _cmd_dismiss(store: AlarmStore, args: str) -> None:
    if not args:
        D.print_error("Usage:  dismiss <id>")
        return
    if store.dismiss(args):
        D.print_success(f"Alarm '{args}' dismissed.")
    else:
        D.print_error(f"No alarm found with ID '{args}'.")
