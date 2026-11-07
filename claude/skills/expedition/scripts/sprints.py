#!/usr/bin/env python3
"""Write sprints.md for a release from ownership.md: the grid of milestones (rows) and
sprints (columns), ticked later by the run.

Usage: python3 -I sprints.py <release> [--owner X] [--root PATH]

Columns come from ownership.md (ownership.py's arithmetic: the longest chain ending at a
milestone plus one). The file holds "# <release> sprints", an "Updated:" line and the grid
"| Milestone | S1 | ... |" only: "·" in a milestone's own column, blank elsewhere. Cells
are "·", "[ ]", "[x]" or "[!]".

When sprints.md exists, a row that still exists keeps every cell as it is once it carries a
run mark ("[ ]", "[x]", "[!]"); a row with only "·" is placed again, except a fix
row, which keeps its cells. New rows are added; a
new fix milestone goes in the running column (the first column holding a "[ ]", else the
last). A row no longer in ownership.md is dropped, unless it carries a run mark: then it is
kept with a warning.

Rows: every milestone of a spec that carries a "- Epic: E<n>" line (new_spec.py --epic), and
every fix milestone. A later epic's independent milestones join an existing column, a running
one too; dependent ones open the next. Row text is the epic label, the spec number and the
milestone name, "E1 01 Filtering" ("fix <name>" for a fix milestone); rows sorted by epic,
spec number, then ownership.md order. The talker reruns it on go, the runner on merge.
"""
import argparse
import datetime
import importlib.util
import re
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
RUN_MARKS = ("[ ]", "[x]", "[!]")
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


def running_column(n, rows):
    """First column holding a "[ ]", else the last one (1-based); 0 when there is no grid."""
    for i in range(n):
        if any(cells[i] == "[ ]" for _, cells in rows):
            return i + 1
    return n


def build(release, milestones, col, existing, num_key, label=None):
    """Return (text, warnings) for sprints.md. label maps a milestone name to its epic number
    (None for a fix milestone)."""
    n_old, rows_old = existing
    label = label or {}
    old = dict(rows_old)
    warnings = []
    run_col = running_column(n_old, rows_old)
    names = [m["name"] for m in milestones]
    spec = {m["name"]: m["spec"] for m in milestones}
    order = {m["name"]: i for i, m in enumerate(milestones)}
    place = {}
    for name in names:
        cells = old.get(name)
        if cells is not None and (marked(cells) or spec[name] == "fix"):
            place[name] = list(cells)
        elif cells is None and spec[name] == "fix" and run_col:
            place[name] = run_col
        else:
            place[name] = col[name]
    kept = []
    for name, cells in rows_old:
        if name not in col and marked(cells):
            kept.append(name)
            place[name] = list(cells)
            warnings.append(f"row '{name}' is not in ownership.md or in no epic but carries a mark: kept")
    width = max([n_old] + [v for v in place.values() if isinstance(v, int)] + [1])

    def cells_of(name):
        v = place[name]
        if isinstance(v, int):
            return [PLANNED if i + 1 == v else "" for i in range(width)]
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
    ownership = folder / "ownership.md"
    milestones, err = own.read_ownership(ownership)
    if err:
        die(err)
    specs = folder / "specs"
    if specs.is_dir():
        newer = [p for p in specs.glob("*.md") if p.stat().st_mtime > ownership.stat().st_mtime]
        if newer:
            die(f"ownership.md older than specs/{newer[0].name}: run ownership.py first")
    col, _, errors, _ = own.schedule(milestones)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        die("ownership.md does not schedule: run ownership.py")
    path = folder / "sprints.md"
    n_old, rows_old, _ = read_grid(path, own)
    label = epic_rows(folder, own, milestones)
    milestones = [m for m in milestones if m["name"] in label or m["spec"] == own.FIX]
    text, warnings = build(release, milestones, col, (n_old, rows_old), own.num_key, label)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    path.write_text(text, encoding="utf-8")
    if not quiet:
        print(path)
    return text


def main():
    ap = argparse.ArgumentParser(usage="sprints.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load_ownership()
    root = own.repo_root(a.root)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    write(folder, a.release)


if __name__ == "__main__":
    main()
