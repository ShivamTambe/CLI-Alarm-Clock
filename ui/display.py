"""
ui/display.py
-------------
All terminal rendering: colors, banner, menu, alarm table, fire alert.
Zero business logic — only formatting and printing.
"""

from __future__ import annotations

import datetime
import sys
import time
from typing import List

from models.alarm import Alarm

# ── ANSI color setup ───────────────────────────────────────────────────────

def _enable_ansi_windows() -> None:
    """Enable VT100/ANSI on Windows 10+ via ctypes SetConsoleMode."""
    try:
        import ctypes
        import ctypes.wintypes
        k32    = ctypes.windll.kernel32
        handle = k32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        mode   = ctypes.wintypes.DWORD()
        k32.GetConsoleMode(handle, ctypes.byref(mode))
        k32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def _setup_colors() -> None:
    import platform
    try:
        import colorama
        colorama.init(autoreset=True)
    except ImportError:
        if platform.system() == "Windows":
            _enable_ansi_windows()


_setup_colors()

# Colour constants
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# State → color mapping
_STATE_COLOR = {
    "pending":   GREEN,
    "snoozed":   BLUE,
    "dismissed": YELLOW,
    "cancelled": DIM,
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _ts_to_str(ts: float) -> str:
    """Format a Unix timestamp as a readable local time string."""
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S  %d %b %Y")


def _countdown(secs: float) -> str:
    """Return a human-readable countdown string."""
    if secs <= 0:
        return f"{RED}OVERDUE{RESET}"
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ── Public rendering functions ─────────────────────────────────────────────

def print_banner() -> None:
    now = datetime.datetime.now().strftime("%I:%M:%S %p  |  %A, %d %B %Y")
    print(f"""
{CYAN}{BOLD}  ╔══════════════════════════════════════════════╗
  ║       ⏰   CLI  ALARM  CLOCK   ⏰            ║
  ║   Set alarms in seconds — simple & precise   ║
  ╚══════════════════════════════════════════════╝{RESET}
  {DIM}Current time: {now}{RESET}
""")


def print_menu() -> None:
    print(f"""
{BOLD}  Commands:{RESET}
  {GREEN}set   <seconds> [label]{RESET}   — Set alarm (e.g. {DIM}set 300 Coffee break{RESET})
  {CYAN}list{RESET}                      — List all alarms
  {YELLOW}del   <id>{RESET}                — Delete alarm by ID
  {BLUE}snooze <id> [seconds]{RESET}     — Snooze a fired alarm  (default: 300 s)
  {MAGENTA}dismiss <id>{RESET}              — Dismiss a fired alarm
  {RED}clear{RESET}                     — Remove ALL alarms
  {BOLD}help{RESET}                      — Show this menu
  {RED}quit{RESET}                      — Exit
""")


def print_alarm_table(alarms: List[Alarm]) -> None:
    """Render all alarms as a formatted table."""
    if not alarms:
        print(f"  {YELLOW}No alarms configured.{RESET}\n")
        return

    header = f"  {BOLD}{'ID':<10}{'FIRES AT':<24}{'COUNTDOWN':<14}{'STATE':<12}LABEL{RESET}"
    sep    = "  " + "─" * 68
    print(f"\n{header}\n{sep}")

    for a in alarms:
        color   = _STATE_COLOR.get(a.state, RESET)
        cdown   = _countdown(a.seconds_remaining) if a.active else f"{DIM}—{RESET}"
        fires_at = _ts_to_str(a.timestamp)
        print(
            f"  {CYAN}{a.id:<10}{RESET}"
            f"{fires_at:<24}"
            f"{cdown:<14}"
            f"{color}{a.state:<12}{RESET}"
            f"{a.label}"
        )
    print()


def print_fire_alert(alarm: Alarm) -> None:
    """Print the full-screen firing notification for a triggered alarm."""
    fires_at = _ts_to_str(alarm.timestamp)
    label    = alarm.label
    aid      = alarm.id
    # Box width = 46 inner chars
    print(f"\n{RED}{BOLD}")
    print("  ╔══════════════════════════════════════════════╗")
    print(f"  ║  🔔  ALARM FIRED!                           ║")
    print(f"  ║  ⏱  Scheduled : {fires_at:<28}║")
    print(f"  ║  📝  Label     : {label:<28}║")
    print(f"  ║  🆔  ID        : {aid:<28}║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  {YELLOW}snooze {aid} [secs]{RED}   dismiss {aid}  ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(RESET)
    # Re-draw the prompt so the user sees where to type
    sys.stdout.write(f"{YELLOW}  > {RESET}")
    sys.stdout.flush()


def print_success(msg: str) -> None:
    print(f"  {GREEN}✓  {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"  {RED}✗  {msg}{RESET}")


def print_info(msg: str) -> None:
    print(f"  {CYAN}ℹ  {msg}{RESET}")
