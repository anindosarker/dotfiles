#!/usr/bin/env python3
"""Set or remove the hold of a decision: the owner's "hold D<n>" (spec 10, module 1.6.1, D17).

Usage: python3 -I decisions/hold.py <release> D<n> [--until <id> | --reason "<text>"] [--owner X] [--root PATH]
       python3 -I decisions/hold.py <release> D<n> --off [--owner X] [--root PATH]

The hold is stored in status/data/status.json, in the entry "decisions.D<n>" (lib/status.py,
lib/decisions.py, the hold): "hold": "yes" with no flag; "hold": "until <id>" with --until (a
queue item, a decision or an epic; the hold is over when <id> is done or archived); "hold":
"yes" and "hold_reason": "<text>" with --reason. A second call replaces both keys. --off removes
both. The command changes no other key of the entry and no line of the decision file.

Under the .ids.lock lock: the two keys written, the status rule on every decision file
(lib/decisions.py sync_files), the keys read back, one plan commit of the status file (and of a
decision file the status rule changed), then the page data written again (status.data.js and
the dashboard data). Prints one line: "D14: held", "D14: held until Q8", "D9: held, <text>" or
"D14: hold off". --off on a decision with no hold prints "D14: hold off" and changes nothing.

Refused with one line, before anything is written: a release whose decisions are not files (a
release below format 2.2, or one of format 2.2 that keeps the decisions.md board; the line names
scripts/migrate/v2.1-v2.2); an id with no decision file; a hold on a decision that is not to-do
or blocked; an --until id that no queue item, decision or epic has; --until with the decision's
own id; --until and --reason in one call; an empty --reason; --off with --until or --reason.
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
TARGET_RE = re.compile(r"^[QDE]\d+$")  # an id a hold can wait for: a queue item, a decision, an epic
USAGE = 'decisions/hold.py <release> D<n> [--until <id> | --reason "<text>" | --off] [--owner X] [--root PATH]'
die = C.die


def main():
    ap = argparse.ArgumentParser(usage=USAGE)
    ap.add_argument("release")
    ap.add_argument("id")
    ap.add_argument("--until", help="the queue item, decision or epic whose close ends the hold, like Q8")
    ap.add_argument("--reason", help="the owner's reason in words")
    ap.add_argument("--off", action="store_true", help="remove the hold")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    m = D_RE.match(a.id)
    if not m:
        die(f"bad id '{a.id}', expected like D7")
    ident = f"D{int(m.group(1))}"
    num = int(m.group(1))
    if a.off and (a.until is not None or a.reason is not None):
        die("--off takes no --until and no --reason: give --off alone")
    if a.until is not None and a.reason is not None:
        die("give --until or --reason, not both: a hold until an id ends by itself, a hold with a reason on the owner's word")
    if a.reason is not None and not a.reason.strip():
        die('the --reason is empty: give the owner\'s words, like --reason "first the trial of the page", or leave --reason out')
    until = a.until.strip() if a.until is not None else None
    if until is not None and not TARGET_RE.match(until):
        die(f"bad --until id '{until}', expected a queue item, a decision or an epic, like Q8, D9 or E3")
    if until == ident:
        die(f"--until {until} is the decision itself: name the queue item, decision or epic the hold waits for")
    dc = C.load("lib/decisions")
    st = C.load("lib/status")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    if not dc.file_form(folder):
        dc.board_refusal(folder, "decisions/hold.py")
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cards = dc.file_cards(folder)
        if num not in {c["num"] for c in cards}:
            die(f"{ident} has no file in {folder / dc.DECISIONS_DIR}: check the id in decisions.md")
        entry = st.decision_entries(folder).get(ident) or {}
        if a.off:
            if not any(k in entry for k in dc.HOLD_KEYS):
                fcntl.flock(lock, fcntl.LOCK_UN)
                print(f"{ident}: hold off")
                return
            want = {"hold": None, "hold_reason": None}
            line = f"{ident}: hold off"
        else:
            word = dc.rule_status(folder, cards)[num]
            if word not in dc.OPEN_WORDS:
                die(f"{ident} is {word}: only a decision that is to-do or blocked can be held")
            if until is not None and until not in dc.id_statuses(folder, cards):
                die(f"--until {until}: no queue item, decision or epic has that id; check the id")
            if until is not None:
                want = {"hold": f"{dc.HOLD_UNTIL}{until}", "hold_reason": None}
                line = f"{ident}: held until {until}"
            elif a.reason is not None:
                want = {"hold": dc.HOLD_YES, "hold_reason": a.reason.strip()}
                line = f"{ident}: held, {a.reason.strip()}"
            else:
                want = {"hold": dc.HOLD_YES, "hold_reason": None}
                line = f"{ident}: held"
        st.set_decision(folder, ident, **want)
        moved = dc.sync_files(folder)
        got = st.decision_entries(folder).get(ident) or {}
        if any(got.get(k) != v for k, v in want.items()):  # read back the keys just written
            die(f"{ident}: the hold was not stored as expected in {st.path(folder)} "
                f"(got {{hold: {got.get('hold')!r}, hold_reason: {got.get('hold_reason')!r}}}); "
                f"restore the file from git and run the call again")
        if (got.get("round"), got.get("files")) != (entry.get("round"), entry.get("files")):
            die(f"{ident}: round or files changed in {st.path(folder)}: restore the file from git and run the call again")
        extra = dc.commit_paths(folder) if moved else []
        st.commit(root, folder, extra, f"docs(plan): {a.release} {line}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    st.write_page_data(folder)  # after the commit: "changed" is read from git
    print(line)


if __name__ == "__main__":
    main()
