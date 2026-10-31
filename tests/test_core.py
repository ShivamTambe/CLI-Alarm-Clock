"""
tests/test_core.py
------------------
Synchronous unit tests for models and core logic.
No background threads are started -- AlarmWatcher is NOT tested here.
Run with:  python tests/test_core.py
"""

from __future__ import annotations

import io
import os
import sys
import time
import datetime

# Force UTF-8 output so Unicode chars work on Windows cp1252 consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point store at a temp file so tests never touch real alarms.json
import core.store as _cs
_TEST_DB = os.path.join(os.path.dirname(__file__), "_test_alarms.json")
_cs._DEFAULT_PATH = _TEST_DB

from models.alarm import Alarm
from core.store   import AlarmStore

# ── Tiny test harness ──────────────────────────────────────────────────────

_failures: list[str] = []

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"

def ok(name: str) -> None:
    print(f"  {GREEN}PASS{RESET}  {name}")

def fail(name: str, detail: str = "") -> None:
    msg = f"  {RED}FAIL{RESET}  {name}" + (f"  —  {detail}" if detail else "")
    print(msg)
    _failures.append(name)

def check(name: str, cond: bool, detail: str = "") -> None:
    ok(name) if cond else fail(name, detail)


# ── Tests: Alarm dataclass ─────────────────────────────────────────────────

def test_alarm_model() -> None:
    print("\n[1] Alarm dataclass")
    now = time.time()

    a = Alarm(timestamp=now + 60, label="Coffee")
    check("default id is 8 chars",      len(a.id) == 8)
    check("default active=True",        a.active is True)
    check("default fired=False",        a.fired  is False)
    check("state == pending",           a.state  == "pending")
    check("seconds_remaining ~60",      59 < a.seconds_remaining < 61)

    # State matrix
    a.fired = True;  check("active+fired -> snoozed",    a.state == "snoozed")
    a.active = False; check("!active+fired -> dismissed", a.state == "dismissed")
    a.fired = False;  check("!active+!fired -> cancelled", a.state == "cancelled")


def test_alarm_serialisation() -> None:
    print("\n[2] Alarm serialisation")
    now = time.time()
    a   = Alarm(timestamp=now + 120, label="Meeting")

    d = a.to_dict()
    check("to_dict has all keys",
          all(k in d for k in ("id","timestamp","label","active","fired")))

    b = Alarm.from_dict(d)
    check("round-trip id",        b.id        == a.id)
    check("round-trip timestamp", b.timestamp == a.timestamp)
    check("round-trip label",     b.label     == a.label)
    check("round-trip active",    b.active    == a.active)
    check("round-trip fired",     b.fired     == a.fired)


# ── Tests: AlarmStore ──────────────────────────────────────────────────────

def test_store_add_list() -> None:
    print("\n[3] AlarmStore.add / list_all")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()

    a = store.add(delay_seconds=300, label="Stand-up")
    alarms = store.list_all()
    check("add returns Alarm",        isinstance(a, Alarm))
    check("list_all count == 1",      len(alarms) == 1)
    check("label stored",             alarms[0].label == "Stand-up")
    check("status pending after add", alarms[0].state == "pending")
    check("timestamp ~300s away",     299 < alarms[0].seconds_remaining < 301)


def test_store_get() -> None:
    print("\n[4] AlarmStore.get")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()
    a = store.add(10, "X")

    found = store.get(a.id)
    check("get by full id",           found is not None and found.id == a.id)
    check("get by prefix",            store.get(a.id[:4]) is not None)
    check("get missing returns None", store.get("xxxxxxxx") is None)


def test_store_delete() -> None:
    print("\n[5] AlarmStore.delete")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()
    a = store.add(10, "Delete Me")

    check("delete returns True",      store.delete(a.id))
    check("list empty after delete",  store.list_all() == [])
    check("delete missing → False",   not store.delete("xxxxxxxx"))


def test_store_snooze() -> None:
    print("\n[6] AlarmStore.snooze")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()
    a = store.add(10, "Snooze Me")

    ok_snooze = store.snooze(a.id, extra_seconds=120)
    updated   = store.get(a.id)
    check("snooze returns True",       ok_snooze)
    check("timestamp shifted ~120s",   119 < updated.seconds_remaining < 121)
    check("active=True after snooze",  updated.active is True)
    check("fired=True after snooze",   updated.fired  is True)
    check("state == snoozed",          updated.state  == "snoozed")


def test_store_dismiss() -> None:
    print("\n[7] AlarmStore.dismiss")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()
    a = store.add(10, "Dismiss Me")

    ok_d    = store.dismiss(a.id)
    updated = store.get(a.id)
    check("dismiss returns True",      ok_d)
    check("active=False",              updated.active is False)
    check("fired=True",                updated.fired  is True)
    check("state == dismissed",        updated.state  == "dismissed")


def test_store_mark_fired() -> None:
    print("\n[8] AlarmStore.mark_fired")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.clear()
    a = store.add(10, "Fire Me")

    store.mark_fired(a.id)
    updated = store.get(a.id)
    check("mark_fired sets fired=True",   updated.fired  is True)
    check("mark_fired sets active=False", updated.active is False)


def test_store_persistence() -> None:
    print("\n[9] JSON persistence round-trip")
    store1 = AlarmStore(persistence_path=_TEST_DB)
    store1.clear()
    a = store1.add(600, "Persist Me")

    # Load from same file in a brand-new store instance
    store2  = AlarmStore(persistence_path=_TEST_DB)
    alarms  = store2.list_all()
    check("loaded count == 1",      len(alarms) == 1)
    check("loaded label matches",   alarms[0].label == "Persist Me")
    check("loaded id matches",      alarms[0].id    == a.id)
    check("loaded timestamp close", abs(alarms[0].timestamp - a.timestamp) < 0.01)
    store2.clear()


def test_store_clear() -> None:
    print("\n[10] AlarmStore.clear")
    store = AlarmStore(persistence_path=_TEST_DB)
    store.add(10, "A")
    store.add(20, "B")
    store.clear()
    check("list empty after clear", store.list_all() == [])


# ── Runner ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 50)
    print("  alarm_clock — unit tests")
    print("=" * 50)

    test_alarm_model()
    test_alarm_serialisation()
    test_store_add_list()
    test_store_get()
    test_store_delete()
    test_store_snooze()
    test_store_dismiss()
    test_store_mark_fired()
    test_store_persistence()
    test_store_clear()

    # Cleanup temp DB
    for p in [_TEST_DB, _TEST_DB + ".tmp"]:
        if os.path.exists(p):
            os.remove(p)

    print("\n" + "=" * 50)
    if _failures:
        print(f"{RED}  {len(_failures)} test(s) FAILED: {_failures}{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}  All tests passed!{RESET}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
