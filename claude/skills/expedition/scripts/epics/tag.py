#!/usr/bin/env python3
"""Epic tags on go (run/go.py runs it): write the epic into the specs, the decisions, the plan
row and the epic file.

Usage: python3 -I epics/tag.py <release> E<n> <spec numbers or D ids> [--owner X] [--root PATH]

A D id resolves to the specs citing it. Each named spec gets the line "- Epic: E<n>" directly
under its title line; each decision those specs cite (and each named D id) gets the tag "#E<n>"
on its card in decisions.md and moves to In progress (lib/decisions.py, under the .ids.lock
lock, then the Done rule sync), and the spec's Deliverables row gets E<n> in
its Epic cell, and plan/epics/E<n>.md gets "Starts: S<n>" under its Specs: line (in a release of
format 2.2, which has no Specs: line, "starts: S<n>" directly after the "status:" line): the current
sprint of the grid as it is at that moment (the first column holding a "[ ]", "[~]" or "·" cell
of another epic's row, else the column after the last column holding another epic's row; S1 for
an empty grid). The grid is status/sprints.md below format 2.2; in a release of format 2.2 it is
read from status/data/status.json (lib/ownership.py grid): the lowest sprint holding a to-do,
in progress or blocked milestone of another epic. An existing Epic line, epic tag or Starts value is kept and reported; a
missing epic file is refused. Each file is read right before its write. Then the Decided cards
of queue.md are synced with the lanes (lib/board.py sync): each card whose decision is now In
progress is ticked and gets "#E<n>". A release of format 2.1 keeps its queue in item files
(lib/queue.py): nothing is synced there, and the line reports none.

Refuses a superseded decision (heading "(superseded by D<n>)", or named by a later
"- Supersedes D<n>." bullet): a named spec that cites one, or a named D id that is one.
Commits nothing. In a release of format 2.2 the status chain runs at the end (epics/table.py
chain): with its "starts:" value the epic is counted from its specs, no longer "waits for
delegate".

A release whose decisions are files (lib/decisions.py file_form): each decision gets the line
"epic: E<n>" in its file in place of the tag, then the status rule makes it in progress. A
decision with an "epic" line keeps it and is printed under "kept:" as on a board. The lines
printed are the same.
"""
import argparse
import fcntl
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
EPIC_RE = re.compile(r"^E\d+$")
die = C.die


def tag_epic(folder, epic, items):
    """Write "- Epic: E<n>" into each named spec (a D id names the specs citing it),
    "#E<n>" on each decision those specs cite and each named D id, and the epic's
    "Starts: S<n>" line."""
    own = C.load("lib/ownership")
    epic_file = folder / own.EPICS_DIR / f"{epic}.md"
    if not epic_file.is_file():
        die(f"{epic_file} missing: run epics/new.py first")
    files = dict(own.spec_files(folder))
    nums, specs = set(), set()
    for item in items:
        d = re.match(r"^D(\d+)$", item)
        if d:
            nums.add(int(d.group(1)))
            hit = [num for num, p in files.items() if int(d.group(1)) in own.spec_cites(p)]
            if not hit:
                print(f"{item}: no spec cites it")
            specs.update(hit)
        elif item in files:
            specs.add(item)
        else:
            die(f"'{item}' is neither a spec number with a file nor a D id")
    own.refuse_superseded(folder, nums, "named D id")
    for num in sorted(specs, key=own.num_key):
        own.refuse_superseded(folder, own.spec_cites(files[num]), f"spec {files[num].name}")
        nums |= own.spec_cites(files[num])
    dc = C.load("lib/decisions")
    in_files = dc.file_form(folder)
    path = dc.path_of(folder)
    if not in_files and not path.is_file():
        die(f"decisions.md missing: {path}")
    tags = own.read_tags(folder)
    missing = sorted(nums - set(tags))
    if missing:
        die(f"no file in {folder / dc.DECISIONS_DIR}: {', '.join(f'D{n}' for n in missing)}" if in_files
            else f"not in decisions.md: {', '.join(f'D{n}' for n in missing)}")
    marked, kept_specs = [], []
    for num in sorted(specs, key=own.num_key):
        old = own.spec_epic(files[num])
        if old:
            kept_specs.append(f"{num} E{old}")
            continue
        elines = files[num].read_text(encoding="utf-8").splitlines(keepends=True)
        title = next((i for i, l in enumerate(elines) if l.startswith("# ")), None)
        if title is None:
            die(f"{files[num].name} has no title line")
        elines.insert(title + 1, f"- Epic: {epic}\n")
        files[num].write_text("".join(elines), encoding="utf-8")
        marked.append(num)
    print(f"{epic} specs: {', '.join(marked) or 'none'}")
    start = f"S{own.current_sprint(folder, exclude=int(epic[1:]))}"
    kept_start = own.set_starts(epic_file, start)
    print(f"{epic} Starts: {kept_start} kept" if kept_start else f"{epic} Starts: {start}")
    plan = folder / f"{folder.parent.name}-plan.md"
    if plan.is_file():
        plines = plan.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, l in enumerate(plines):
            r = C.ROW_RE.match(l.lstrip())
            cells = l.rstrip("\n").split("|")
            if r and r.group(1) in specs and len(cells) >= 6 and not cells[3].strip():
                cells[3] = f" {epic} "
                plines[i] = "|".join(cells) + "\n"
        plan.write_text("".join(plines), encoding="utf-8")
    else:
        print(f"warning: {plan.name} missing, Epic cells not written")
    if kept_specs:
        print(f"kept specs: {', '.join(kept_specs)}")
    tagged, kept = [], []
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if in_files:
            moved = tag_files(folder, epic, nums, dc, tagged, kept)
            fcntl.flock(lock, fcntl.LOCK_UN)
            return report(epic, tagged, moved, kept, folder, own, dc)
        text = path.read_text(encoding="utf-8")
        cards = {c["num"]: c for c in dc.parse(text)["cards"]}
        for n in sorted(nums):
            c = cards[n]
            if c["epic"]:
                kept.append(f"D{n} E{c['epic']}" + (" done" if c["lane"] == dc.DONE else ""))
                continue
            c["epic"] = int(epic[1:])
            lane = dc.DONE if c["lane"] == dc.DONE else dc.PROGRESS
            text = dc.move(text, n, lane, dc.head_line(c, lane))
            tagged.append(n)
        if tagged:
            C.load("lib/board").write(path, text)
        moved = dc.sync_file(folder)
        fcntl.flock(lock, fcntl.LOCK_UN)
    report(epic, tagged, moved, kept, folder, own, dc)


def tag_files(folder, epic, nums, dc, tagged, kept):
    """The line "epic: E<n>" in the file of each decision without one, then the status rule.
    Fills tagged and kept; returns the files the status rule changed."""
    cards = {c["num"]: c for c in dc.file_cards(folder)}
    for n in sorted(nums):
        c = cards[n]
        if c["epic"]:
            kept.append(f"D{n} E{c['epic']}" + (" done" if c["lane"] == dc.DONE else ""))
            continue
        p = c["path"]
        p.write_text(dc.set_front(p.read_text(encoding="utf-8"), epic=epic), encoding="utf-8")
        tagged.append(n)
    moved = dc.sync_file(folder)
    if tagged:
        dc.write_data(folder)
    return [(n, old, new) for n, old, new in moved if n not in tagged] if moved else moved


def report(epic, tagged, moved, kept, folder, own, dc):
    """The lines of tag_epic after the decisions are tagged."""
    print(f"{epic}: {', '.join(f'D{n}' for n in sorted(tagged)) or 'nothing tagged'}")
    if moved:
        print(f"decisions.md lanes synced: {dc.moved_text(moved)}")
    if kept:
        print(f"kept: {', '.join(sorted(kept, key=lambda k: int(k.split()[0][1:])))}")
    bd = C.load("lib/board")
    changed = [] if C.load("lib/queue").item_form(folder) else \
        bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder), C.lock_file(folder))
    print(f"queue.md cards ticked and tagged: {', '.join(f'Q{n}' for n in changed) or 'none'}")

def main():
    ap = argparse.ArgumentParser(
        usage="epics/tag.py <release> E<n> <spec numbers or D ids> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("epic")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not EPIC_RE.match(a.epic):
        die(f"bad epic '{a.epic}', expected like E3")
    items = [s.strip() for x in a.rest for s in x.split(",") if s.strip()]
    if not items:
        die("needs spec numbers or D ids")
    root = C.repo_root(a.root, a.release)
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    tag_epic(folder, a.epic, items)
    C.load("epics/table").chain(folder, a.release)


if __name__ == "__main__":
    main()
