#!/usr/bin/env python3
"""Write "Starts: S<n>" into the epic file of every epic that has rows in status/sprints.md and
no Starts value, once per release whose epics predate the Starts line.

Usage: python3 -I sprints/backfill_starts.py <release> [--dry-run] [--owner X] [--root PATH]

The value is the lowest column among the epic's finished rows ("[x]", "[!]"), else the current
sprint (that epic's own rows ignored). It commits nothing and prints the value per epic and
every row whose column changes at the next sprints/refresh.py run, with its old and new column.
Finished rows never move: the grid keeps their cells; a running row carries its "[ ]" to its new
column. --dry-run writes nothing. Then run sprints/check.py and sprints/refresh.py.
"""
import argparse
import collections
import importlib.util
import re
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


def backfill_starts(own, folder, dry_run=False):
    """Starts for every epic with grid rows and an epic file without one."""
    n, rows = own.grid(folder)
    starts = own.epic_starts(folder)
    by_epic = collections.defaultdict(list)
    for label, cells in rows:
        m = re.match(r"^E(\d+)\s", label)
        if m:
            by_epic[int(m.group(1))].append((label, cells))
    written = {}
    for e in sorted(by_epic):
        path = folder / own.EPICS_DIR / f"E{e}.md"
        if not path.is_file():
            print(f"E{e}: no epic file, no floor")
            continue
        if starts.get(e):
            print(f"E{e}: Starts: {starts[e]} kept")
            continue
        done = [i + 1 for _, cells in by_epic[e] for i, c in enumerate(cells) if c in ("[x]", "[!]")]
        value = f"S{min(done)}" if done else f"S{own.current_sprint(folder, exclude=e)}"
        why = "lowest finished column" if done else "current sprint"
        print(f"E{e}: Starts: {value} ({why})")
        written[e] = value
        if not dry_run:
            own.set_starts(path, value)
    milestones, errors = own.collect(folder)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return
    fl = own.floors(folder, milestones)
    for name, epic in own.epic_of_milestones(folder, milestones).items():
        if epic in written:
            fl[name] = int(written[epic][1:])
    col, _, errs, _ = own.schedule(milestones, fl, own.started_columns(folder, milestones))
    for e in errs:
        print(f"error: {e}", file=sys.stderr)
    if errs:
        return
    sp = C.load("lib/grid")
    label = sp.epic_rows(folder, own, milestones)
    shown = [m for m in milestones if m["name"] in label]
    text, _ = sp.build(folder.parent.name, shown, col, (n, [(sp.row_name(l), c) for l, c in rows]),
                       own.num_key, label)
    _, new_rows = own.table_rows(text, "Milestone")
    before = {sp.row_name(l): c for l, c in rows}
    moved = []
    for r in new_rows:
        name, cells = sp.row_name(r[0]), r[1:]
        old_at = next((i + 1 for i, x in enumerate(before.get(name, [])) if x), None)
        new_at = next((i + 1 for i, x in enumerate(cells) if x), None)
        if old_at and old_at != new_at:
            mark = next((x for x in cells if x), "")
            moved.append(f"  {r[0]} {mark}: S{old_at} to S{new_at}")
    print(f"rows that move: {len(moved) or 'none'}")
    for line in moved:
        print(line)
    print("dry run; nothing written" if dry_run else "nothing committed")


def main():
    ap = argparse.ArgumentParser(usage="sprints/backfill_starts.py <release> [--dry-run] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true", help="write nothing")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    backfill_starts(own, folder, a.dry_run)


if __name__ == "__main__":
    main()
