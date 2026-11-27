#!/usr/bin/env python3
"""Move a release folder to the five milestone statuses (reference/formats.md, Milestone status).

Usage: python3 -I migrate/v0.0-v0.1/statuses.py <release> [--dry-run] [--owner X] [--root PATH]

In the release folder of the main checkout: every tracker "Status: merged (...)" becomes
"Status: done (...)" and every "Status: skipped (...)" becomes "Status: stopped (...)"; every
"[ ]" cell of status/sprints.md whose tracker says waiting becomes "[~]". The tracker is read as
status/progress.py reads it: the most advanced copy among the main checkout and the milestone's
own worktree. Then, under the .ids.lock lock, the grid chain of sprints/refresh.py when a cell
changed, the swimlane data (sprints/swimlanes.py), and one commit of the trackers, the grid, the
epic files, decisions.md and queue.md that changed, never pushed.

Prints one line per change. --dry-run prints the same and writes nothing. A second run changes
nothing. No other script refuses an unconverted folder: the readers take merged and skipped as
done and stopped, and nothing writes them any more.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import re
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
OLD_STATUS_RE = re.compile(r"^(Status:[ \t]*)(merged|skipped)\b", re.M)


def new_status(own, text):
    """The tracker text with the old word of its Status line replaced, or None when it has none."""
    line = own.STATUS_RE.search(text)
    m = OLD_STATUS_RE.match(text, line.start()) if line else None
    if not m:
        return None
    word = own.OLD_STATUS[m.group(2)]
    return text[:m.start(2)] + word + text[m.end(2):]


def waiting_rows(own, root, folder, release):
    """[(milestone name, Status value)] of the "[ ]" grid rows whose tracker says waiting."""
    pg, g = C.load("status/progress"), C.load("lib/grid")
    _, rows, _ = g.read_grid(folder / C.SPRINTS_MD)
    blocks = own.new_collect(folder, folder / f"{release}-plan.md")["blocks"]
    trackers = {b["name"]: b["tracker"] for bl in blocks.values() for b in bl}
    wts, out = None, []
    for name, cells in rows:
        if g.mark_of(cells) != "[ ]" or name not in trackers:
            continue
        wts = wts if wts is not None else pg.worktrees(root)
        status = pg.tracker_state(own, trackers[name].relative_to(root), wts)
        if status and status[0] == "waiting":
            out.append((name, status[2]))
    return out


def main():
    ap = argparse.ArgumentParser(usage="migrate/v0.0-v0.1/statuses.py <release> [--dry-run] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    own, g = C.load("lib/ownership"), C.load("lib/grid")
    grid = folder / C.SPRINTS_MD
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        trackers = []
        for p in sorted((folder / C.TRACKERS_DIR).glob("*-tracker.md")):
            text = own.read(p)
            new = new_status(own, text)
            if new is not None:
                trackers.append((p, new))
                print(f"{p.relative_to(folder)}: {own.status_value(text)[2]} to {own.status_value(new)[2]}")
        waits = waiting_rows(own, root, folder, a.release) if grid.is_file() else []
        for name, value in waits:
            print(f"{C.SPRINTS_MD}: {name}: [ ] to [~] (tracker: {value})")
        if a.dry_run:
            print("dry run; nothing written")
            return
        for p, new in trackers:
            p.write_text(new, encoding="utf-8")
        for name, _ in waits:
            _, text = g.set_mark(grid, name, g.MARKS["wait"])
            grid.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            if waits:
                g.refresh(folder, a.release, quiet=True, locked=True)
            if grid.is_file():
                C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
        paths = [p for p, _ in trackers]
        if waits:
            paths += [grid, folder / "decisions.md", folder / C.QUEUE_MD] + sorted((folder / C.EPICS_DIR).glob("E*.md"))
        done = C.commit(root, paths, f"docs(plan): {a.release} five milestone statuses") if paths else False
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{len(trackers)} trackers, {len(waits)} grid cells changed; committed" if done else "nothing to change")


if __name__ == "__main__":
    main()
