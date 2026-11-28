#!/usr/bin/env python3
"""The grid of a release, built from the ownership facts (lib/ownership.py compute, in memory):
milestones (rows) and sprints (columns). Library, no CLI. Below format 2.2 it is the file
status/sprints.md. In a release of format 2.2 (spec 04, D13) no file is written or read: the
grid text is built from status/data/status.json and returned (sprints/grid.py prints it), and
the status file holds each milestone's sprint (lib/status.py).

Columns are the ownership arithmetic: the longest chain ending at a milestone plus one, never
before its epic's "Starts: S<n>" line in plan/epics/E<n>.md. The file holds "# <release> sprints",
an "Updated:" line and the grid "| Milestone | S1 | ... |" only: "·" in a milestone's own column,
blank elsewhere. Cells are "·", "[ ]", "[~]", "[x]" or "[!]" (reference/formats.md, Milestone
status).

When status/sprints.md exists (a release with no status file; a release with one, of any format,
reads these rows from its status file instead, stored_rows), a row that still exists keeps every cell as it is once it is
finished ("[x]" or "[!]"). Every other row is placed again; a running or waiting row carries its
"[ ]" or "[~]" to its new column. A row whose milestone no longer exists is dropped, unless it carries a run
mark: then it is kept with a warning. A "[~]" of a milestone never launched (lib/ownership.py
held_unlaunched) is no run mark here.

Rows: every milestone of a spec that carries a "- Epic: E<n>" line (epics/tag.py). An epic's
milestones start at its start sprint (the current sprint at its go), a milestone added after go
at its own "- Starts: S<n>" line (plan/milestone.py); dependent ones open the next column. Row text
is the epic label, the spec number and the milestone name, "E1 01 Filtering"; rows sorted by
epic, spec number, then milestone order in the spec.

write_grid() writes the grid only (sprints/grid.py); in format 2.2 it returns the text and writes
no file. refresh() is the chain every grid change runs, in this order: the grid (in format 2.2
the placement, stored in the status file by lib/status.py sync); the Sprint column of the "## Ownership" table of every unfinished
epic that has gone (a Starts value, not every decision in Done), touching only that column
(lib/ownership.py sync_sprint_columns), finished epics' files left alone; then the cards of
decisions.md moved to the lanes of the Done rule (lib/decisions.py sync), so a merge reaches
the board; then the Decided cards of queue.md synced with those lanes (lib/board.py sync: the
tick and the #E<n> tag; nothing in a release of format 2.1, whose decided items hold their
decision id only, lib/queue.py). sprints/refresh.py,
sprints/mark.py, run/go.py (through sprints/refresh.py) and plan/milestone.py use
refresh(); the swimlane data (sprints/swimlanes.py) follows it. set_mark() sets one run cell for
sprints/mark.py, the only writer of the marks; resume_mark() is the cell a resume sets.
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
RUN_MARKS = ("[ ]", "[~]", "[x]", "[!]")
FINISHED = ("[x]", "[!]")
STARTED = ("[ ]", "[~]")
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
    """The run mark a row carries, "·" when it has none."""
    return next((c for c in cells if c in RUN_MARKS), PLANNED)


def build(release, milestones, col, existing, num_key, label=None, held=(), view=False, updated=False):
    """Return (text, warnings) for the grid. label maps a milestone name to its epic number;
    held names the "[~]" rows never launched. view: the marks of a release with status.json, as
    {status word of its format: mark}, for the legend line; False for an earlier release.
    updated: an "Updated:" line in the view too (format 2.2, whose grid is printed on demand)."""
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
        if name not in col and name not in held and marked(cells):
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
    if view:
        legend = ", ".join(f"`{m}` {w}" for w, m in view.items())
        stamp = f"Updated: {now:%Y-%m-%d %H:%M}\n\n" if updated else ""
        return f"# {release} sprints\n\n{stamp}{head}\n{sep}\n{body}\nMarks: {legend}.\n", warnings
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
    """Write status/sprints.md; returns (text, the ownership facts). In a release of format 2.2
    the text is built from the status file and returned, and no file is written or read."""
    own = C.load("lib/ownership")
    comp = compute_or_die(own, folder)
    milestones, col = comp["milestones"], comp["col"]
    st = C.load("lib/status")
    new = st.new_form(folder)
    n_old, rows_old = 0, []
    if not new:
        path = folder / C.SPRINTS_MD
        path.parent.mkdir(exist_ok=True)
        n_old, rows_old, _ = read_grid(path)
    label = epic_rows(folder, own, milestones)
    milestones = [m for m in milestones if m["name"] in label]
    view = st.active(folder) and {st.say(folder, w): m for w, m in st.MARKS.items()}
    if view:
        n_old, rows_old = stored_rows(st, folder)
    text, warnings = build(release, milestones, col, (n_old, rows_old), C.num_key, label,
                           () if view else own.held_unlaunched(folder), view, updated=new)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if new:
        return text, comp
    path.write_text(text, encoding="utf-8")
    if not quiet:
        print(path)
    return text, comp


def stored_rows(st, folder):
    """(column count, rows) of the grid as status.json holds it: each milestone's mark, from its
    status, in the column of its sprint. The grid file is a view of this, never read back."""
    rows = []
    for m in st.entries(folder)[0].values():
        if m.get("sprint"):
            c = int(m["sprint"][1:])
            rows.append((m["name"], [""] * (c - 1) + [st.MARKS[m["status"]]]))
    n = max([len(c) for _, c in rows] + [0])
    return n, [(name, c + [""] * (n - len(c))) for name, c in rows]


def grid_files(folder):
    """The grid file a commit of the chain holds: [status/sprints.md] below format 2.2, [] in a
    release of format 2.2, which has none."""
    return [] if C.load("lib/status").new_form(folder) else [folder / C.SPRINTS_MD]


def sync_epics(folder, comp):
    """The Sprint column of every unfinished epic's table, from the grid (lib/ownership.py grid:
    the status file in format 2.2, status/sprints.md below); prints each file."""
    for p in C.load("lib/ownership").sync_sprint_columns(folder, comp):
        print(f"{p}: Sprint column synced with the grid")


def sync_decisions(folder, locked=False):
    """The cards of decisions.md, to the lanes of the Done rule; prints the cards moved. In the
    file form of the decisions the status rule on every decision file and the list
    (lib/decisions.py sync_files): prints "decisions: D9 to in progress" and writes the dashboard
    data again when a file changed. Takes the .ids.lock lock unless the caller holds it
    (locked=True)."""
    dc = C.load("lib/decisions")
    moved = dc.sync_file(folder, None if locked else C.lock_file(folder))
    if moved and dc.file_form(folder):
        print(f"decisions: {dc.moved_text(moved)}")
        dc.write_data(folder)  # the status chain wrote the dashboard data before this step
    elif moved:
        print(f"{folder / 'decisions.md'}: lanes synced: {dc.moved_text(moved)}")


def sync_queue(folder, locked=False):
    """The Decided cards of queue.md, from the lanes of decisions.md; prints the cards. Takes
    the .ids.lock lock unless the caller holds it (locked=True). Nothing in a release of format
    2.1 (item files, lib/queue.py): a decided item holds its decision id only."""
    if C.load("lib/queue").item_form(folder):
        return
    own, bd = C.load("lib/ownership"), C.load("lib/board")
    lock = None if locked else C.lock_file(folder)
    changed = bd.sync_file(folder / C.QUEUE_MD, bd.decision_tags(own, folder), lock)
    if changed:
        print(f"{folder / C.QUEUE_MD}: synced with decisions.md: {', '.join(f'Q{n}' for n in changed)}")


def refresh(folder, release, quiet=False, locked=False):
    """The chain after a grid change: the grid, the epic files' Sprint column, the decisions
    lanes, the queue sync. locked=True: the caller holds the .ids.lock lock. Returns the grid text.
    In a release of format 2.2 the status file is written before the Sprint column, because the
    placement is stored there and the column is read from there (no grid file)."""
    text, comp = write_grid(folder, release, quiet)
    st = C.load("lib/status")
    if st.new_form(folder):
        st.sync(folder, release)
        sync_epics(folder, comp)
    else:
        sync_epics(folder, comp)
        if st.active(folder):
            st.sync(folder, release)
    sync_decisions(folder, locked)
    sync_queue(folder, locked)
    return text


MARKS = {"launch": "[ ]", "wait": "[~]", "merge": "[x]", "stop": "[!]"}
ACTIONS = sorted(MARKS) + ["resume"]
WAITABLE = STARTED + (PLANNED,)


def resume_mark(folder, key):
    """The cell a resume sets on the "[~]" cell of the milestone with tracker key key: "[ ]" when
    it was launched before (lib/ownership.py launched_keys: its "launched" value in the status
    file in format 2.2, a sprints/mark.py launch commit in the history of status/sprints.md
    below), "·" when it never was. "[ ]" when git cannot tell."""
    keys = C.load("lib/ownership").launched_keys(folder)
    return "[ ]" if keys is None or key in keys else PLANNED


def set_mark(path, name, mark):
    """status/sprints.md (a release with no status file) with the run cell of the row of milestone name set to mark, in the
    column the row has now. Returns (old cell, new text), or (None, None) when no row names it."""
    lines = C.read(path).split("\n")
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or row_name(cells[0]) != name or cells[0] == "Milestone":
            continue
        at = next((k for k, c in enumerate(cells[1:], 1) if c), None)
        if at is None:
            return None, None
        old = cells[at]
        cells[at] = mark
        lines[i] = "| " + " | ".join(cells) + " |"
        return old, "\n".join(lines)
    return None, None
