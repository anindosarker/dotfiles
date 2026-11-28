#!/usr/bin/env python3
"""Supersede a built decision: mark both sides in decisions.md (reference/formats.md, decisions.md).

Usage: python3 -I decisions/supersede.py <release> D<old> D<new> [--owner X] [--root PATH]

Under the .ids.lock lock: the old card gets "(superseded by D<new>)" at the end of its title and
the tag "#superseded", and moves to Done, ticked; the new card gets "- Supersedes D<old>." as its
first bullet (kept when it is there already). Refuses an unknown id, the same id twice, and an
old decision that is superseded already. Then the Done rule sync of decisions.md and the
Decided-card sync of queue.md, and one commit, never pushed. Sending "NOTE D<old>: superseded by
D<new>" to the other session stays a session step. Prints one line. A release of format 2.1
keeps its queue in item files (lib/queue.py): no queue sync there.

A release whose decisions are files (lib/decisions.py file_form): the old file gets
"status: archived" and "replaced_by: D<new>"; its title line is not changed. The new file is not
changed: its body is free, and "replaced_by" of the old file holds the link. The same refusals
(an id with no file, the same id twice, an old decision with a "replaced_by" line already). Then
the status rule on every decision file and the list, one commit of decisions.md and the decision
files, and the dashboard data written again (lib/dashboard.py). The last line is the same.
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
D_RE = re.compile(r"^D(\d+)$")
die = C.die


def main():
    ap = argparse.ArgumentParser(usage="decisions/supersede.py <release> D<old> D<new> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    for x in (a.old, a.new):
        if not D_RE.match(x):
            die(f"bad id '{x}', expected like D7")
    old, new = int(a.old[1:]), int(a.new[1:])
    if old == new:
        die(f"{a.old} cannot supersede itself")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    dc, bd, own = C.load("lib/decisions"), C.load("lib/board"), C.load("lib/ownership")
    if dc.file_form(folder):
        return supersede_file(a, root, folder, old, new, dc)
    path = dc.path_of(folder)
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        text = path.read_text(encoding="utf-8")
        cards = {c["num"]: c for c in dc.parse(text)["cards"]}
        missing = [x for x, n in ((a.old, old), (a.new, new)) if n not in cards]
        if missing:
            die(f"not in {path}: {', '.join(missing)}")
        o = cards[old]
        if o["sup_by"]:
            die(f"{a.old} is superseded already by D{o['sup_by'][0]}")
        o["sup_by"] = [new]
        text = dc.move(text, old, dc.DONE, dc.head_line(o, dc.DONE))
        n = next(c for c in dc.parse(text)["cards"] if c["num"] == new)
        first = next((l for l in n["body"] if l.strip()), "")
        if not re.match(rf"^\s*-\s*Supersedes D{old}\b", first):
            lines = text.split("\n")
            lines.insert(n["line"] + 1, f"\t- Supersedes D{old}.")
            text = "\n".join(lines)
        bd.write(path, text)
        dc.sync_file(folder)
        Q = C.load("lib/queue")
        if not Q.item_form(folder):  # format 2.1: a decided item holds its decision id only
            bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder))
        C.commit(root, [path, *Q.commit_paths(folder)], f"docs(plan): {a.release} {a.old} superseded by {a.new}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.old} superseded by {a.new}, to Done; committed")


def supersede_file(a, root, folder, old, new, dc):
    """supersede.py on decision files: the old file archived, with replaced_by."""
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cards = {c["num"]: c for c in dc.file_cards(folder)}
        missing = [x for x, n in ((a.old, old), (a.new, new)) if n not in cards]
        if missing:
            die(f"no file in {folder / dc.DECISIONS_DIR}: {', '.join(missing)}")
        if cards[old]["sup_by"]:
            die(f"{a.old} is superseded already by D{cards[old]['sup_by'][0]}")
        dc.set_fields(folder, old, status="archived", replaced_by=f"D{new}")
        got = next(c for c in dc.file_cards(folder) if c["num"] == old)["status"]
        if got != "archived":  # the status rule must keep what this command stored
            die(f"{a.old} is {got} after the status rule, not archived: restore {cards[old]['path']} from git")
        C.commit(root, dc.commit_paths(folder), f"docs(plan): {a.release} {a.old} superseded by {a.new}")
        dc.write_data(folder)  # after the commit: "changed" is read from git
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.old} superseded by {a.new}, to Done; committed")


if __name__ == "__main__":
    main()
