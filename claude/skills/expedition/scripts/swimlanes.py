#!/usr/bin/env python3
"""Write the swimlane data of a release: status/data/sprints.json and status/data/sprints.data.js
(the same JSON as a script, so status/index.html also opens from file://).

Usage: python3 -I swimlanes.py <release> [--owner X] [--root PATH]

Reads status/sprints.md (grid), status/ownership.md (table and "## Critical paths") and
<release>-plan.md (Deliverables). Each epic's path milestones are marked critical; the data
holds criticalPaths {"E6": [names]} and criticalPath, their union, for older pages.
Refreshes status/index.html from templates/swimlanes.html when the template is newer or the
page is missing. Both are renders, ignored by git (new_cycle.py and migrate_layout.py add
the .gitignore lines), never committed. Writes nothing else. The lead runs it at go, the runner on merge, after
sprints.py.
"""
import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
NUM = r"\d{2}(?:\.\d+)?"
PLAN_ROW_RE = re.compile(r"^\|\s*(" + NUM + r")\s*\|\s*\[(.+?)\]\((.+?)\)\s*\|\s*(E\d+)?\s*\|\s*(.+?)\s*\|\s*$", re.M)
GRID_LABEL_RE = re.compile(r"^(E\d+)\s+(" + NUM + r")\s+(.+)$")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "swimlanes.html"


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


def status_of(marker):
    return "done" if marker == "[x]" else "running" if marker == "[ ]" else "planned"


def build(folder, release, own):
    """The swimlane data dict of a release folder."""
    sprints_path, own_path = folder / own.SPRINTS_MD, folder / own.OWNERSHIP_MD
    for p in (sprints_path, own_path):
        if not p.is_file():
            die(f"{p.relative_to(folder)} missing: run ownership.py and sprints.py")
    sprints_md = own.read(sprints_path)
    plan = folder / f"{release}-plan.md"
    plan_md = own.read(plan) if plan.is_file() else ""
    updated = re.search(r"^Updated: (.+)$", sprints_md, re.M)

    specs = {m.group(1): {"title": m.group(2), "spec": m.group(3), "outcome": m.group(5)}
             for m in PLAN_ROW_RE.finditer(plan_md)}
    owned, err = own.read_ownership(own_path)
    if err:
        die(err)
    owners = {m["name"]: m for m in owned}
    paths = {f"E{e}": names for e, names in sorted(own.read_paths(own_path).items())}
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
        if m:
            epic, number, name = m.groups()
        else:
            fix = re.match(r"^fix\s+(.+)$", label)
            epic, number, name = "Fixes", None, fix.group(1) if fix else label
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
    epics = []
    for ms in milestones:
        if ms["epic"] not in epics:
            epics.append(ms["epic"])
    epics.sort(key=lambda e: (e == "Fixes", int(e[1:]) if e[1:].isdigit() else 0))
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
    ap = argparse.ArgumentParser(usage="swimlanes.py <release> [--owner X] [--root PATH]")
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
