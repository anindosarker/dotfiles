#!/usr/bin/env python3
"""The status/sprints.md grid of a release, built from the ownership facts (lib/ownership.py
compute, in memory): milestones (rows) and sprints (columns). Library, no CLI.

Columns are the ownership arithmetic: the longest chain ending at a milestone plus one, never
before its epic's "Starts: S<n>" line in plan/epics/E<n>.md. The file holds "# <release> sprints",
an "Updated:" line and the grid "| Milestone | S1 | ... |" only: "·" in a milestone's own column,
blank elsewhere. Cells are "·", "[ ]", "[x]" or "[!]".

When status/sprints.md exists, a row that still exists keeps every cell as it is once it is
finished ("[x]" or "[!]"). Every other row is placed again; a running row carries its "[ ]"
to its new column. A row whose milestone no longer exists is dropped, unless it carries a run
mark: then it is kept with a warning.

Rows: every milestone of a spec that carries a "- Epic: E<n>" line (epics/tag.py). An epic's
milestones start at its start sprint (the current sprint at its go), a milestone added after go
at its own "- Starts: S<n>" line (plan/new_fix.py); dependent ones open the next column. Row text
is the epic label, the spec number and the milestone name, "E1 01 Filtering"; rows sorted by
epic, spec number, then milestone order in the spec.

write_grid() writes the grid only (sprints/grid.py). refresh() is the chain every grid change
runs, in this order: the grid; the Sprint column of the "## Ownership" table of every unfinished
epic that has gone (a Starts value, not every decision [Done]), touching only that column
(lib/ownership.py sync_sprint_columns), finished epics' files left alone; then the Decided cards
of queue.md synced with the tag lines of decisions.md (lib/board.py sync: the tick and the
#E<n> tag), so a "[Done]" written since the last script run reaches the board. sprints/refresh.py,
run/go.py (through sprints/refresh.py), plan/new_fix.py and migrate/fixes.py use refresh(); the
swimlane data (sprints/swimlanes.py) follows it.
"""
import datetime
import importlib.util
import re
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
RUN_MARKS = ("[ ]", "[x]", "[!]")
FINISHED = ("[x]", "[!]")
PLANNED = "·"
ROW_PREFIX_RE = re.compile(r"^E\d+\s+\d{2}(?:\.\d+)?\s+(.*)$")


def row_name(text):
    """Milestone name of a grid row, without the epic label and spec number."""
    m = ROW_PREFIX_RE.match(text)
    return m.group(1) if m else text


def read_grid(path, own=None):
    """Existing grid: (column count, rows as [(name, cells)], column labels) from the
    "| Milestone" table. Row names lose their prefix."""
    if not path.is_file():
        return 0, [], []
    head, data = C.table_rows(C.read(path), "Milestone")
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


def build(release, milestones, col, existing, num_key, label=None):
    """Return (text, warnings) for status/sprints.md. label maps a milestone name to its epic number."""
    n_old, rows_old = existing
    label = label or {}
    old = dict(rows_old)
    warnings = []
    names = [m["name"] for m in milestones]
    spec = {m["name"]: m["spec"] for m in milestones}
    order = {m["name"]: i for i, m in enumerate(milestones)}
    place = {}
    for name in names:
        cells = old.get(name)
        if cells is not None and finished(cells):
            place[name] = list(cells)
        else:
            place[name] = (col[name], mark_of(cells or []))
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

    old_order = {name: i for i, (name, _) in enumerate(rows_old)}
    rows = sorted(names + kept, key=lambda n: (
        label.get(n) or 10 ** 6, num_key(spec.get(n)), order.get(n, len(order) + old_order.get(n, 0))))
    now = datetime.datetime.now()
    head = "| Milestone | " + " | ".join(f"S{i + 1}" for i in range(width)) + " |"
    sep = "|---|" + "---|" * width
    show = lambda name: f"E{label[name]} {spec[name]} {name}" if label.get(name) else name
    body = "".join(f"| {show(name)} | " + " | ".join(cells_of(name)) + " |\n" for name in rows)
    text = f"# {release} sprints\n\nUpdated: {now:%Y-%m-%d %H:%M}\n\n{head}\n{sep}\n{body}"
    return text, warnings


def epic_rows(folder, own, milestones):
    """{milestone name: epic number} for every milestone whose spec carries an Epic line."""
    epics = own.spec_epics(folder)
    return {m["name"]: epics[m["spec"]][0] for m in milestones
            if m["spec"] in epics and epics[m["spec"]][0]}


def compute_or_die(own, folder):
    """The ownership facts; dies when the milestones do not schedule."""
    comp = own.compute(folder)
    if comp["errors"]:
        for e in comp["errors"]:
            print(f"error: {e}", file=sys.stderr)
        C.die("the milestones do not schedule: fix the specs (sprints/check.py names the error)")
    return comp


def write_grid(folder, release, quiet=False):
    """Write status/sprints.md; returns (text, the ownership facts)."""
    own = C.load("lib/ownership")
    comp = compute_or_die(own, folder)
    milestones, col = comp["milestones"], comp["col"]
    path = folder / C.SPRINTS_MD
    path.parent.mkdir(exist_ok=True)
    n_old, rows_old, _ = read_grid(path)
    label = epic_rows(folder, own, milestones)
    milestones = [m for m in milestones if m["name"] in label]
    text, warnings = build(release, milestones, col, (n_old, rows_old), C.num_key, label)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    path.write_text(text, encoding="utf-8")
    if not quiet:
        print(path)
    return text, comp


def sync_epics(folder, comp):
    """The Sprint column of every unfinished epic's table, from the grid; prints each file."""
    for p in C.load("lib/ownership").sync_sprint_columns(folder, comp):
        print(f"{p}: Sprint column synced with the grid")


def sync_queue(folder):
    """The Decided cards of queue.md, from the tag lines of decisions.md; prints the cards."""
    own, bd = C.load("lib/ownership"), C.load("lib/board")
    changed = bd.sync_file(folder / C.QUEUE_MD, bd.decision_tags(own, folder), folder / ".ids.lock")
    if changed:
        print(f"{folder / C.QUEUE_MD}: synced with decisions.md: {', '.join(f'Q{n}' for n in changed)}")


def refresh(folder, release, quiet=False):
    """The chain after a grid change: the grid, the epic files' Sprint column, the queue sync.
    Returns the grid text."""
    text, comp = write_grid(folder, release, quiet)
    sync_epics(folder, comp)
    sync_queue(folder)
    return text
