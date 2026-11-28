#!/usr/bin/env python3
"""Write the decider of a decision file that has none: who made the call (D9). With --change,
replace the decider of a file that has one (Q29).

Usage: python3 -I decisions/decider.py <release> D<n> you|lead|agent [--change] [--owner X] [--root PATH]

For a decision recorded before its release moved to decision files (a decision recorded in a
file has its "decider" line from queue/item.py D --decider). Under the .ids.lock lock: the
"decider" line goes after the "status" line of decisions/D<n>-<slug>.md (lib/decisions.py, the
order of the front matter), nothing else of the file changes; then the status rule on every
decision file and the list, one commit of decisions.md and the decision files, and the
dashboard data written again (lib/dashboard.py). Prints one line.

Refused, before anything is written: a word that is not you, lead or agent; an id with no file;
without --change, a file that has a "decider" line ("D<n> has decider <word>"); with --change, a
file whose "decider" line already holds the word ("D<n> has decider <word> already"). --change on
a file with no "decider" line writes it, as without the flag. A release whose decisions are on
the decisions.md board is refused with one line that names scripts/migrate/v2.1-v2.2.
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
    ap = argparse.ArgumentParser(usage="decisions/decider.py <release> D<n> you|lead|agent [--change] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("id")
    ap.add_argument("word")
    ap.add_argument("--change", action="store_true", help="replace the decider line of a file that has one")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    m = D_RE.match(a.id)
    if not m:
        die(f"bad id '{a.id}', expected like D7")
    num = int(m.group(1))
    dc = C.load("lib/decisions")
    if a.word not in dc.DECIDERS:
        die(f"bad decider '{a.word}': you, lead or agent")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    if not dc.file_form(folder):
        dc.board_refusal(folder, "decisions/decider.py")
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        card = next((c for c in dc.file_cards(folder) if c["num"] == num), None)
        if card is None:
            die(f"{a.id} has no file in {folder / dc.DECISIONS_DIR}")
        if card["decider"] and not a.change:
            die(f"{a.id} has decider {card['decider']}: nothing changed")
        if card["decider"] == a.word:
            die(f"{a.id} has decider {a.word} already: nothing changed")
        old = card["decider"]
        path = dc.set_fields(folder, num, decider=a.word)
        if dc.front_of(C.read(path)).get("decider") != a.word:  # read back the line just written
            die(f"{path} has no decider line after the write: restore it from git")
        msg = f"decider {old} to {a.word}" if old else f"decider {a.word}"
        C.commit(root, dc.commit_paths(folder), f"docs(plan): {a.release} {a.id} {msg}")
        dc.write_data(folder)  # after the commit: "changed" is read from git
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.id} decider {old} to {a.word}; committed" if old else f"{a.id} decider {a.word}; committed")


if __name__ == "__main__":
    main()
