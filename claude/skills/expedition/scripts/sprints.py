#!/usr/bin/env python3
"""Write status/sprints.md for a release from the ownership facts (ownership.compute, in memory):
the grid of milestones (rows) and sprints (columns), ticked later by the run.

Usage: python3 -I sprints.py <release> [--owner X] [--root PATH]

Columns are ownership.py's arithmetic: the longest chain ending at a milestone plus one, never
before its epic's "Starts: S<n>" line in plan/epics/E<n>.md. The file holds "# <release> sprints", an "Updated:" line and the grid
"| Milestone | S1 | ... |" only: "·" in a milestone's own column, blank elsewhere. Cells
are "·", "[ ]", "[x]" or "[!]".

When status/sprints.md exists, a row that still exists keeps every cell as it is once it is
finished ("[x]" or "[!]"). Every other epic row is placed again; a running row carries its
"[ ]" to its new column. Fix rows (no epic) are placed after the epic rows: a new fix row, and
an unfinished one left of the current sprint, go to the current sprint with their mark; an
unfinished fix row at or right of it stays. The current sprint is the first column holding a
"[ ]" or "·" cell of an epic row, else the column after the last column holding an epic row (S1
on an empty grid). A row whose milestone no longer exists is dropped, unless it carries a run
mark: then it is kept with a warning.

Rows: every milestone of a spec that carries a "- Epic: E<n>" line (new_spec.py --epic), and
every fix milestone. An epic's milestones start at its start sprint (the current sprint at its
go); dependent ones open the next column. Row text is the epic label, the spec number and the
milestone name, "E1 01 Filtering" ("fix <name>" for a fix milestone); rows sorted by epic,
spec number, then milestone order in the spec. The lead reruns it on go, the runner on merge.

It then rewrites the Sprint column of the "## Ownership" table of every unfinished epic that has
gone (a Starts value, not every decision [Done]) from the new grid, touching only that column
(ownership.sync_sprint_columns); finished epics' files are left alone. The runner commits the
epic files it changed together with the grid.

It also syncs the Decided cards of queue.md with the tag lines of decisions.md (board.sync: the
tick and the #E<n> tag), so a "[Done]" written since the last script run reaches the board.
"""
import argparse
import datetime
import importlib.util
import re
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
RUN_MARKS = ("[ ]", "[x]", "[!]")
FINISHED = ("[x]", "[!]")
PLANNED = "·"


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_ownership():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "ownership.py"
    spec = importlib.util.spec_from_file_location("ownership", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ROW_PREFIX_RE = re.compile(r"^(?:E\d+\s+\d{2}(?:\.\d+)?|fix)\s+(.*)$")


def row_name(text):
    """Milestone name of a grid row, without the epic label and spec number (or "fix")."""
    m = ROW_PREFIX_RE.match(text)
    return m.group(1) if m else text


def read_grid(path, own):
    """Existing grid: (column count, rows as [(name, cells)], column labels) from the
    "| Milestone" table. Row names lose their prefix."""
    if not path.is_file():
        return 0, [], []
    head, data = own.table_rows(own.read(path), "Milestone")
    if head is None:
        return 0, [], []
    n = len(head) - 1
    rows = [(row_name(r[0]), (r[1:] + [""] * n)[:n]) for r in data if r and r[0]]
    return n, rows, head[1:]


def marked(cells):
    return any(c in RUN_MARKS for c in cells)


def finished(cells):
    return any(c in FINISHED for c in cells)


def mark_of(cells):
    """The run mark a row carries ("[ ]" or "·"), "·" when it has none."""
    return next((c for c in cells if c in RUN_MARKS), PLANNED)


def current_column(cells_by_row, epic_rows):
    """The first column holding a "[ ]" or "·" cell of an epic row, else the column after the
    last column holding an epic row (1 when there is none). 1-based."""
    width = max((len(c) for c in cells_by_row.values()), default=0)
    epic = [cells_by_row[n] for n in epic_rows if n in cells_by_row]
    for i in range(width):
        if any(i < len(c) and c[i] in ("[ ]", PLANNED) for c in epic):
            return i + 1
    used = [i + 1 for c in epic for i, x in enumerate(c) if x]
    return max(used) + 1 if used else 1


def build(release, milestones, col, existing, num_key, label=None):
    """Return (text, warnings) for status/sprints.md. label maps a milestone name to its epic number
    (None for a fix milestone)."""
    n_old, rows_old = existing
    label = label or {}
    old = dict(rows_old)
    warnings = []
    names = [m["name"] for m in milestones]
    spec = {m["name"]: m["spec"] for m in milestones}
    order = {m["name"]: i for i, m in enumerate(milestones)}
    place = {}
    fixes = [n for n in names if spec[n] == "fix"]
    for name in names:
        cells = old.get(name)
        if cells is not None and finished(cells):
            place[name] = list(cells)
        elif name not in fixes:
            place[name] = (col[name], mark_of(cells or []))
    epic_rows = [n for n in names if n not in fixes]

    def as_cells(v, width):
        if isinstance(v, tuple):
            return [v[1] if i + 1 == v[0] else "" for i in range(max(width, v[0]))]
        return list(v)
    width0 = max([n_old] + [v[0] for v in place.values() if isinstance(v, tuple)] + [1])
    cur = current_column({n: as_cells(place[n], width0) for n in epic_rows}, epic_rows)
    for name in fixes:
        if name in place:
            continue
        cells = old.get(name)
        at = next((i + 1 for i, c in enumerate(cells or []) if c), None)
        place[name] = (at if at and at >= cur else cur, mark_of(cells or []))
    kept = []
    for name, cells in rows_old:
        if name not in col and marked(cells):
            kept.append(name)
            place[name] = list(cells)
            warnings.append(f"row '{name}' is no milestone or in no epic but carries a mark: kept")
    width = max([n_old] + [v[0] for v in place.values() if isinstance(v, tuple)] + [1])

    def cells_of(name):
        v = place[name]
        if isinstance(v, tuple):
            return [v[1] if i + 1 == v[0] else "" for i in range(width)]
        return (v + [""] * width)[:width]

    def first_col(name):
        c = cells_of(name)
        return next((i for i, x in enumerate(c) if x), width)

    old_order = {name: i for i, (name, _) in enumerate(rows_old)}
    rows = sorted(names + kept, key=lambda n: (
        label.get(n) or 10 ** 6, num_key(spec.get(n, "fix")), order.get(n, len(order) + old_order.get(n, 0))))
    now = datetime.datetime.now()
    head = "| Milestone | " + " | ".join(f"S{i + 1}" for i in range(width)) + " |"
    sep = "|---|" + "---|" * width
    show = lambda name: (f"E{label[name]} {spec[name]} {name}" if label.get(name)
                         else f"fix {name}" if spec.get(name, "fix") == "fix" else name)
    body = "".join(f"| {show(name)} | " + " | ".join(cells_of(name)) + " |\n" for name in rows)
    text = f"# {release} sprints\n\nUpdated: {now:%Y-%m-%d %H:%M}\n\n{head}\n{sep}\n{body}"
    return text, warnings


def epic_rows(folder, own, milestones):
    """{milestone name: epic number} for every milestone whose spec carries an Epic line."""
    epics = own.spec_epics(folder)
    return {m["name"]: epics[m["spec"]][0] for m in milestones
            if m["spec"] in epics and epics[m["spec"]][0]}


def write(folder, release, quiet=False):
    own = load_ownership()
    comp = own.compute(folder)
    if comp["errors"]:
        for e in comp["errors"]:
            print(f"error: {e}", file=sys.stderr)
        die("the milestones do not schedule: fix the specs (ownership.py names the error)")
    milestones, col = comp["milestones"], comp["col"]
    path = folder / own.SPRINTS_MD
    path.parent.mkdir(exist_ok=True)
    n_old, rows_old, _ = read_grid(path, own)
    label = epic_rows(folder, own, milestones)
    milestones = [m for m in milestones if m["name"] in label or m["spec"] == own.FIX]
    text, warnings = build(release, milestones, col, (n_old, rows_old), own.num_key, label)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    path.write_text(text, encoding="utf-8")
    if not quiet:
        print(path)
    for p in own.sync_sprint_columns(folder, comp):
        print(f"{p}: Sprint column synced with the grid")
    bd = own.load_sibling("board")
    changed = bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder), folder / ".ids.lock")
    if changed:
        print(f"{folder / own.QUEUE_MD}: synced with decisions.md: {', '.join(f'Q{n}' for n in changed)}")
    return text


def main():
    ap = argparse.ArgumentParser(usage="sprints.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load_ownership()
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    write(folder, a.release)


if __name__ == "__main__":
    main()
