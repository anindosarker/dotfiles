#!/usr/bin/env python3
"""Epic tags on go (run/go.py runs it): write the epic into the specs, the decisions, the plan
row and the epic file.

Usage: python3 -I epics/tag.py <release> E<n> <spec numbers or D ids> [--owner X] [--root PATH]

A D id resolves to the specs citing it. Each named spec gets the line "- Epic: E<n>" directly
under its title line; each decision those specs cite (and each named D id) gets the tag line
"[E<n>]" directly under its heading in decisions.md, and the spec's Deliverables row gets E<n> in
its Epic cell, and plan/epics/E<n>.md gets "Starts: S<n>" under its Specs: line: the current
sprint of status/sprints.md as it is at that moment (the first column holding a "[ ]" or "·"
cell of another epic's row, else the column after the last column holding another epic's row;
S1 for an empty grid). An existing Epic line, epic tag or Starts value is kept and reported; a
missing epic file is refused. Each file is read right before its write. Then the Decided cards
of queue.md are synced with the tag lines (lib/board.py sync): each card whose decision now
carries "[E<n>]" is ticked and gets "#E<n>".

Refuses a superseded decision (heading "(superseded by D<n>)", or named by a later
"- Supersedes D<n>." bullet): a named spec that cites one, or a named D id that is one.
Commits nothing.
"""
import argparse
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
    "[E<n>]" under each decision those specs cite and each named D id, and the epic's
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
    path = folder / "decisions.md"
    if not path.is_file():
        die(f"decisions.md missing: {path}")
    tags = own.read_tags(folder)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    missing = sorted(nums - set(tags))
    if missing:
        die(f"not in decisions.md: {', '.join(f'D{n}' for n in missing)}")
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
    for n in sorted(nums, key=lambda n: -tags[n]["line"]):
        t = tags[n]
        if t["epic"]:
            kept.append(f"D{n} E{t['epic']}" + (" done" if t["done"] else ""))
            continue
        lines.insert(t["line"] + 1, f"[{epic}]\n")
        tagged.append(n)
    path.write_text("".join(lines), encoding="utf-8")
    print(f"{epic}: {', '.join(f'D{n}' for n in sorted(tagged)) or 'nothing tagged'}")
    if kept:
        print(f"kept: {', '.join(sorted(kept, key=lambda k: int(k.split()[0][1:])))}")
    bd = C.load("lib/board")
    changed = bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder), folder / ".ids.lock")
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


if __name__ == "__main__":
    main()
