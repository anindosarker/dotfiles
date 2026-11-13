#!/usr/bin/env python3
"""Close a decision with nothing to run: its card in decisions.md moves to Done, ticked.

Usage: python3 -I decisions/close.py <release> D<n> [--owner X] [--root PATH]

The ticked card in Done is the record (lib/decisions.py, Done rule 3): a later sync keeps it in
Done while no epic that has gone has a row for it. Under the .ids.lock lock: refuses a decision
that is not in decisions.md, carries an epic tag, or has a row in an epic that has gone (its
work closes it on merge); a decision already in Done changes nothing. Then the Done rule sync of
decisions.md and the Decided-card sync of queue.md (the card ticked without "#E"), and one
commit of the files that changed, never pushed. Prints one line.
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
    ap = argparse.ArgumentParser(usage="decisions/close.py <release> D<n> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("id")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    m = D_RE.match(a.id)
    if not m:
        die(f"bad id '{a.id}', expected like D7")
    num = int(m.group(1))
    root, folder = C.find_folder(a.release, a.owner, a.root)
    dc, bd, own = C.load("lib/decisions"), C.load("lib/board"), C.load("lib/ownership")
    path = folder / "decisions.md"
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        text = path.read_text(encoding="utf-8")
        card = next((c for c in dc.parse(text)["cards"] if c["num"] == num), None)
        if card is None:
            die(f"{a.id} is not in {path}")
        if card["lane"] == dc.DONE and card["ticked"]:
            print(f"{a.id} is already in Done; nothing changed")
            return
        if card["epic"]:
            die(f"{a.id} is in E{card['epic']}: its work closes it on merge")
        if dc.started_rows(folder).get(num):
            die(f"{a.id} has a row in an epic that has gone: its work closes it on merge")
        bd.write(path, dc.move(text, num, dc.DONE, dc.head_line(card, dc.DONE)))
        dc.sync_file(folder)
        bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder))
        C.commit(root, [path, folder / own.QUEUE_MD], f"docs(plan): {a.release} {a.id} closed, nothing to run")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.id} to Done (nothing to run); committed")


if __name__ == "__main__":
    main()
