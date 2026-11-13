#!/usr/bin/env python3
"""Rewrite the Sprint column of the "## Ownership" table of every unfinished epic that has gone
(a Starts value, not every decision [Done]) from status/sprints.md, touching only that column
(lib/ownership.py sync_sprint_columns); finished epics' files are left alone. Prints each file
it changed. Commits nothing.

Usage: python3 -I sprints/sync_epic_sprints.py <release> [--owner X] [--root PATH]

sprints/refresh.py runs it after every grid change.
"""
import argparse
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
    ap = argparse.ArgumentParser(usage="sprints/sync_epic_sprints.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    _, folder = C.find_folder(a.release, a.owner, a.root)
    g = C.load("lib/grid")
    g.sync_epics(folder, g.compute_or_die(C.load("lib/ownership"), folder))


if __name__ == "__main__":
    main()
