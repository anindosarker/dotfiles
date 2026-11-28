#!/usr/bin/env python3
"""Write the status/sprints.md grid of a release from the ownership facts, and nothing else
(lib/grid.py write_grid: columns, rows, cells kept and placed).

In a release of format 2.2 (spec 04, D13) there is no grid file: the command prints the grid on
stdout instead, in the shape the file had ("# <release> sprints", an "Updated:" line, the table
"| Milestone | S1 | ... |" and the "Marks:" legend), built from status/data/status.json, and
writes nothing.

Usage: python3 -I sprints/grid.py <release> [--owner X] [--root PATH]

The epic files' Sprint column and the queue sync follow a grid change: sprints/refresh.py runs
the whole chain, and sessions use it (or sprints/mark.py for a mark) rather than this script.
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
    ap = argparse.ArgumentParser(usage="sprints/grid.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    _, folder = C.find_folder(a.release, a.owner, a.root)
    if C.load("lib/status").new_form(folder):
        text, _ = C.load("lib/grid").write_grid(folder, a.release, quiet=True)
        sys.stdout.write(text)
        return
    C.load("lib/grid").write_grid(folder, a.release)


if __name__ == "__main__":
    main()
