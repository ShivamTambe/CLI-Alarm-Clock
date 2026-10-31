"""
utils/sound.py
--------------
Cross-platform sound alert. No alarm or UI knowledge.
"""

from __future__ import annotations

import platform
import sys
import time


def play_alert() -> None:
    """
    Play an audible alert using the best available method for the OS.

    Priority
    --------
    Windows  → winsound.Beep (built-in, no subprocess)
    macOS    → afplay via subprocess
    Linux    → aplay via subprocess, fallback to terminal bell
    Any      → terminal bell \\a as last resort
    """
    system = platform.system()
    try:
        if system == "Windows":
            _beep_windows()
        elif system == "Darwin":
            _beep_macos()
        else:
            _beep_linux()
    except Exception:
        _bell()


# ── Platform implementations ───────────────────────────────────────────────

def _beep_windows() -> None:
    import winsound  # stdlib, Windows only
    pattern = [(1000, 300), (800, 200), (1000, 300), (800, 200)]
    for freq, dur in pattern:
        winsound.Beep(freq, dur)
        time.sleep(0.05)


def _beep_macos() -> None:
    import subprocess
    subprocess.run(
        ["afplay", "/System/Library/Sounds/Glass.aiff"],
        check=False,
        timeout=3,
    )


def _beep_linux() -> None:
    import subprocess
    result = subprocess.run(
        ["aplay", "/usr/share/sounds/sound-icons/glass-water-1.wav"],
        check=False,
        timeout=3,
    )
    if result.returncode != 0:
        _bell()


def _bell() -> None:
    sys.stdout.write("\a\a\a")
    sys.stdout.flush()
