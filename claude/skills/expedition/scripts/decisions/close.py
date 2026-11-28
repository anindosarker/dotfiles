#!/usr/bin/env python3
"""Close a decision with nothing to run: its card in decisions.md moves to Done, ticked.

Usage: python3 -I decisions/close.py <release> D<n> [--backlog] [--owner X] [--root PATH]

The ticked card in Done is the record (lib/decisions.py, Done rule 3): a later sync keeps it in
Done while no epic that has gone has a row for it. Under the .ids.lock lock: refuses a decision
that is not in decisions.md, carries an epic tag, or has a row in an epic that has gone (its
work closes it on merge); a decision already in Done changes nothing. Then the Done rule sync of
decisions.md and the Decided-card sync of queue.md (the card ticked without "#E"), and one
commit of the files that changed, never pushed. Prints one line. A release of format 2.1 keeps
its queue in item files (lib/queue.py): no queue sync there.

A release whose decisions are files (lib/decisions.py file_form): the file of D<n> gets
"status: done", with the same refusals (no file, an "epic" line, a row in an epic that has gone)
and the same line for a decision that is done already. --backlog stores "status: backlog", for a
decision that moves to another release; it is refused for an id with no file and for a decision
that is done or archived, and in the board form with one line that names scripts/migrate/v2.1-v2.2.
Then the status rule on every decision file and the list, one commit of decisions.md and the
decision files, and the dashboard data written again (lib/dashboard.py).
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
    ap = argparse.ArgumentParser(usage="decisions/close.py <release> D<n> [--backlog] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("id")
    ap.add_argument("--backlog", action="store_true", help="decision files: the decision moves to another release")
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
    if dc.file_form(folder):
        return close_file(a, root, folder, num, dc)
    if a.backlog:
        dc.board_refusal(folder, "decisions/close.py --backlog")
    path = dc.path_of(folder)
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
        Q = C.load("lib/queue")
        if not Q.item_form(folder):  # format 2.1: a decided item holds its decision id only
            bd.sync_file(folder / own.QUEUE_MD, bd.decision_tags(own, folder))
        C.commit(root, [path, *Q.commit_paths(folder)], f"docs(plan): {a.release} {a.id} closed, nothing to run")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.id} to Done (nothing to run); committed")


def close_file(a, root, folder, num, dc):
    """close.py and close.py --backlog on a decision file."""
    word = "backlog" if a.backlog else "done"
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        card = next((c for c in dc.file_cards(folder) if c["num"] == num), None)
        if card is None:
            die(f"{a.id} has no file in {folder / dc.DECISIONS_DIR}")
        if a.backlog:
            if card["status"] in ("done", "archived"):
                die(f"{a.id} is {card['status']}: only a decision that is not done or archived moves to the backlog")
            if card["status"] == "backlog":
                print(f"{a.id} is backlog already; nothing changed")
                return
        else:
            if card["status"] == "done":
                print(f"{a.id} is already in Done; nothing changed")  # the line of the board form
                return
            if card["status"] in ("backlog", "archived"):
                die(f"{a.id} is {card['status']}: it is closed already")
            if card["epic"]:
                die(f"{a.id} is in E{card['epic']}: its work closes it on merge")
            if dc.started_rows(folder).get(num):
                die(f"{a.id} has a row in an epic that has gone: its work closes it on merge")
        dc.set_fields(folder, num, status=word)
        got = next(c for c in dc.file_cards(folder) if c["num"] == num)["status"]
        if got != word:  # the status rule must keep what this command stored
            die(f"{a.id} is {got} after the status rule, not {word}: restore {card['path']} from git")
        what = "moved to the backlog" if a.backlog else "closed, nothing to run"
        C.commit(root, dc.commit_paths(folder), f"docs(plan): {a.release} {a.id} {what}")
        dc.write_data(folder)  # after the commit: "changed" is read from git
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{a.id} to backlog; committed" if a.backlog else f"{a.id} to Done (nothing to run); committed")


if __name__ == "__main__":
    main()
