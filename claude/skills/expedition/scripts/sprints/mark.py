#!/usr/bin/env python3
"""The only writer of the run marks in status/sprints.md: set one milestone's cell, then run the
refresh chain and commit, as one command per event.

Usage: python3 -I sprints/mark.py <release> <milestone> launch|merge|stop [--owner X] [--root PATH]

<milestone> is the milestone's tracker file name without "-tracker.md", for example
47-comparison-page for run/trackers/47-comparison-page-tracker.md (a path or the full file name
is accepted too). The runner and the workflow know it: the tracker path is in the MILESTONES
entry and in every prompt.

launch sets the milestone's cell to "[ ]", merge to "[x]", stop to "[!]", in the column its row
has now. Then, under the .ids.lock lock: the grid is regenerated with a new "Updated:" line, the
Sprint column of every unfinished epic's table, the lanes of decisions.md and the Decided cards
of queue.md follow it (lib/grid.py refresh), the swimlane data is written (sprints/swimlanes.py),
and the grid, the epic files, decisions.md and queue.md the chain changed are committed with
--only, never pushed. Prints one
line.

A milestone with no tracker of that name, or with no row in the grid, is refused with one line,
exit 1. A repeat call (the cell already holds the mark) changes nothing, prints one line and
exits 0.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
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


def milestone_of(own, folder, release, key):
    """(spec number, milestone name, tracker path) of the milestone whose tracker file is
    <key>-tracker.md, or None."""
    blocks = own.new_collect(folder, folder / f"{release}-plan.md")["blocks"]
    for num, bl in blocks.items():
        for b in bl:
            if b["tracker"].name == f"{key}-tracker.md":
                return num, b["name"], b["tracker"]
    return None


def main():
    ap = argparse.ArgumentParser(
        usage="sprints/mark.py <release> <milestone> launch|merge|stop [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("milestone")
    ap.add_argument("action", choices=sorted(C.load("lib/grid").MARKS))
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    key = Path(a.milestone).name.removesuffix(".md").removesuffix("-tracker")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    own, g = C.load("lib/ownership"), C.load("lib/grid")
    hit = milestone_of(own, folder, a.release, key)
    if hit is None:
        C.die(f"no milestone has the tracker {C.TRACKERS_DIR}/{key}-tracker.md")
    num, name, _ = hit
    mark = g.MARKS[a.action]
    grid = folder / C.SPRINTS_MD
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old, text = g.set_mark(grid, name, mark) if grid.is_file() else (None, None)
        if old is None:
            C.die(f"{key}: milestone '{name}' of spec {num} has no row in {C.SPRINTS_MD}")
        if old == mark:
            print(f"{key}: already {mark}, nothing changed")
            return
        grid.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            g.refresh(folder, a.release, quiet=True, locked=True)
            C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
        paths = [grid, folder / "decisions.md", folder / C.QUEUE_MD] + sorted((folder / C.EPICS_DIR).glob("E*.md"))
        C.commit(root, paths, f"docs(plan): {a.release} {key} {a.action}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{key}: {old} to {mark} ({num} {name}); committed")


if __name__ == "__main__":
    main()
