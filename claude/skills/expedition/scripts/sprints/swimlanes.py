#!/usr/bin/env python3
"""Write the swimlane data of a release: status/data/sprints.json and status/data/sprints.data.js
(the same JSON as a script, so status/index.html also opens from file://).

Usage: python3 -I sprints/swimlanes.py <release> [--owner X] [--root PATH]

Reads status/sprints.md (grid), the ownership facts (lib/ownership.py compute, in memory: each
milestone's dependencies and files, each epic's critical path computed on the fly) and
<release>-plan.md (Deliverables). Each epic's path milestones are marked critical; the data
holds criticalPaths {"E6": [names]} and criticalPath, their union, for older pages.
Each milestone's status is one of the five of reference/formats.md, Milestone status, from its
grid cell alone. A waiting or stopped milestone also gets a short reason for its card: what
status/progress.py shows for it without "waits on the " ("owner: <what>"), or for a stopped one
its first ## Attention bullet, else the detail of its tracker's Status line, from the same
tracker copies status/progress.py reads (the milestone's own worktree included); empty when none
is found.
In a release with status/data/status.json none of that is written: the page is
templates/task-board.html, which reads status/data/status.data.js (lib/status.py), and this
script only keeps the page and that file current (refresh_board).
Refreshes status/index.html from templates/swimlanes.html when the template is newer or the
page is missing. Both are renders, ignored by git (plan/new_cycle.py and migrate/v0.0-v0.1/layout.py add
the .gitignore lines), never committed. Writes nothing else. sprints/refresh.py runs it last, after
the grid chain.
"""
import argparse
import importlib.util
import json
import re
import shutil
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

NUM = r"\d{2}(?:\.\d+)?"
PLAN_ROW_RE = re.compile(r"^\|\s*(" + NUM + r")\s*\|\s*\[(.+?)\]\((.+?)\)\s*\|\s*(E\d+)?\s*\|\s*(.+?)\s*\|\s*$", re.M)
GRID_LABEL_RE = re.compile(r"^(E\d+)\s+(" + NUM + r")\s+(.+)$")
TEMPLATE = C.TEMPLATES / "swimlanes.html"


die = C.die


def load_ownership():
    return C.load("lib/ownership")


STATUS = {"[ ]": "running", "[~]": "waiting", "[!]": "stopped", "[x]": "done"}


def status_of(marker):
    return STATUS.get(marker, "planned")


def reasons(folder, release, own, rows):
    """{milestone name: short reason} of the waiting and stopped rows [(name, cell)], read as
    status/progress.py reads the trackers."""
    want = [(n, c) for n, c in rows if status_of(c) in ("waiting", "stopped")]
    if not want:
        return {}
    pg = C.load("status/progress")
    root = next((p.parent for p in folder.parents if p.name == ".ai"), None)
    blocks = own.new_collect(folder, folder / f"{release}-plan.md")["blocks"]
    trackers = {b["name"]: b["tracker"] for bl in blocks.values() for b in bl}
    wts = pg.worktrees(root) if root else []
    out = {}
    for name, cell in want:
        path = trackers.get(name)
        status = pg.tracker_state(own, path.relative_to(root), wts) if path and root else None
        kind, reason, _ = pg.effective(cell, status)
        text = pg.reason_of(own, kind, reason, path)
        if not text and status and status[0] == "stopped":
            text = status[1]
        out[name] = "" if text in (None, "waits") else text.removeprefix("waits on the ")
    return out


def build(folder, release, own):
    """The swimlane data dict of a release folder."""
    sprints_path = folder / own.SPRINTS_MD
    if not sprints_path.is_file():
        die(f"{sprints_path.relative_to(folder)} missing: run sprints/refresh.py")
    sprints_md = own.read(sprints_path)
    plan = folder / f"{release}-plan.md"
    plan_md = own.read(plan) if plan.is_file() else ""
    updated = re.search(r"^Updated: (.+)$", sprints_md, re.M)

    specs = {m.group(1): {"title": m.group(2), "spec": m.group(3), "outcome": m.group(5)}
             for m in PLAN_ROW_RE.finditer(plan_md)}
    comp = own.compute(folder)
    if comp["errors"]:
        for e in comp["errors"]:
            print(f"error: {e}", file=sys.stderr)
        die("the milestones do not schedule: fix the specs (sprints/check.py names the error)")
    owners = {m["name"]: m for m in comp["milestones"]}
    paths = {f"E{e}": names for e, names in sorted(comp["paths"].items())}
    union = [n for names in paths.values() for n in names]

    head, grid = own.table_rows(sprints_md, "Milestone")
    if head is None:
        die("status/sprints.md has no grid whose header starts \"| Milestone\"")
    milestones = []
    for row in grid:
        if not row or not row[0]:
            continue
        label, cells = row[0], row[1:]
        col = next((i for i, c in enumerate(cells) if c), None)
        if col is None:
            continue
        m = GRID_LABEL_RE.match(label)
        if not m:
            continue
        epic, number, name = m.groups()
        o = owners.get(name, {})
        spec = specs.get(number, {}) if number else {}
        milestones.append({
            "id": name,
            "name": name,
            "epic": epic,
            "number": number,
            "sprint": col,
            "status": status_of(cells[col]),
            "marker": cells[col],
            "depends": o.get("deps", []),
            "files": o.get("files", []),
            "specTitle": spec.get("title"),
            "specPath": spec.get("spec"),
            "outcome": spec.get("outcome"),
            "critical": name in paths.get(epic, []),
            "specAbs": str(folder / spec["spec"]) if spec.get("spec") else None,
        })
    why = reasons(folder, release, own, [(ms["name"], ms["marker"]) for ms in milestones])
    for ms in milestones:
        ms["reason"] = why.get(ms["name"], "")
    epics = []
    for ms in milestones:
        if ms["epic"] not in epics:
            epics.append(ms["epic"])
    epics.sort(key=lambda e: int(e[1:]))
    repo = next((p.parent for p in folder.parents if p.name == ".ai"), None)
    return {
        "release": release,
        "repoRoot": str(repo) if repo else None,
        "updated": updated.group(1) if updated else None,
        "source": str(folder),
        "sprints": head[1:],
        "epics": epics,
        "milestones": milestones,
        "criticalPaths": paths,
        "criticalPath": union,
    }


BOARD = C.TEMPLATES / "task-board.html"


def refresh_board(folder):
    """A release with status/data/status.json: status/index.html is templates/task-board.html,
    copied when the page is missing or differs; its data, status.data.js, is written from the
    status file, and the swimlane data files of the earlier page are removed. Returns True when
    the page was written."""
    st = C.load("lib/status")
    st.write_page_data(folder)
    for old in ("sprints.json", "sprints.data.js"):
        (folder / "status" / "data" / old).unlink(missing_ok=True)
    page = folder / "status" / "index.html"
    if not BOARD.is_file():
        die(f"template missing: {BOARD}")
    if not page.is_file() or page.read_bytes() != BOARD.read_bytes():
        shutil.copyfile(BOARD, page)
        return True
    return False


def refresh_page(folder):
    """Copy the template to status/index.html when the page is missing or older."""
    page = folder / "status" / "index.html"
    if not TEMPLATE.is_file():
        die(f"template missing: {TEMPLATE}")
    if not page.is_file() or TEMPLATE.stat().st_mtime > page.stat().st_mtime:
        shutil.copyfile(TEMPLATE, page)
        return True
    return False


def write(folder, release, quiet=False):
    if C.load("lib/status").active(folder):
        page = refresh_board(folder)
        if not quiet:
            print(folder / C.load("lib/status").SCRIPT)
            if page:
                print(folder / "status" / "index.html")
        return None
    own = load_ownership()
    data = build(folder, release, own)
    out = folder / "status" / "data"
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    (out / "sprints.json").write_text(text + "\n", encoding="utf-8")
    (out / "sprints.data.js").write_text(f"window.SPRINT_DATA = {text};\n", encoding="utf-8")
    page = refresh_page(folder)
    if not quiet:
        print(out / "sprints.data.js")
        if page:
            print(folder / "status" / "index.html")
        print(f"{len(data['milestones'])} milestones, {len(data['epics'])} lanes, "
              f"{len(data['sprints'])} sprints, {len(data['criticalPaths'])} epic paths")
    return data


def main():
    ap = argparse.ArgumentParser(usage="sprints/swimlanes.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load_ownership()
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    write(folder, a.release)


if __name__ == "__main__":
    main()
