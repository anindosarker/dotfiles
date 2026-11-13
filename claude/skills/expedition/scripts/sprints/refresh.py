#!/usr/bin/env python3
"""The one command after a change to the specs, the epics or the grid: the chain of lib/grid.py
refresh(), then the swimlane data, in this order:

1. the status/sprints.md grid (sprints/grid.py),
2. the Sprint column of every unfinished epic's table (sprints/sync_epic_sprints.py),
3. the cards of decisions.md moved to the lanes of the Done rule (lib/decisions.py sync),
4. the Decided cards of queue.md synced with those lanes (queue/sync.py),
5. status/data/sprints.data.js and sprints.json (sprints/swimlanes.py).

Usage: python3 -I sprints/refresh.py <release> [--owner X] [--root PATH]

Runs under the .ids.lock lock, so it never interleaves with sprints/mark.py. Prints what each
step prints. Commits nothing: the caller commits the grid together with the epic files,
decisions.md and queue.md the chain changed (run/go.py does).
"""
import argparse
import fcntl
import importlib.util
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()


def main():
    ap = argparse.ArgumentParser(usage="sprints/refresh.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    _, folder = C.find_folder(a.release, a.owner, a.root)
    with open(folder / ".ids.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        C.load("lib/grid").refresh(folder, a.release, locked=True)
        C.load("sprints/swimlanes").write(folder, a.release)
        fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
