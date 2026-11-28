#!/usr/bin/env python3
"""Print the "Waits for you" line of a release of format 2.2: each thing that waits for the
owner, and each decision the owner holds (spec 10, module 1.6.1, D17).

Usage: python3 -I status/waits.py <release> [--skip <id>] [--owner X] [--root PATH]
       python3 -I status/waits.py <release> --new [--skip <id>] [--owner X] [--root PATH]
       python3 -I status/waits.py <release> --held [--owner X] [--root PATH]

The lead makes one call for a message: with no flag in a turn the owner started, with --new in
every other turn. Each form prints the line and records the keys of what it printed, so a call
with no flag followed by --new prints no "new:" line for an entry the first call already
printed: never make two calls for one message.

The rows are built at each call by lib/dashboard.py build from the plan files and the status
file, so the line is never older than the files (status/data/dashboard.json is not read). One
entry per row that waits, in this order: epics, decisions, tasks, milestones, queue items; inside
a kind in the order of the numbers; joined by " · ":
- epic, blocked, turn you (planned, waits for delegate): "E3 planned: delegate"
- decision, ready: "D14 ready: compose"; ready with a hold that is over: "D14: hold over, ready: compose"
- task, turn you: "05-04: your look" (the row's label)
- milestone, turn you, and none of its tasks has an entry: "<label>: <the reason>", without a
  leading "owner: "
- queue item, turn you: "Q18: record it"
- a decision held (a hold that is not over, lib/decisions.py hold_state) and to-do or blocked:
  no entry; its id is in the last part, "Held: D9, D14", ids only, in the order of the numbers.
The line is "Waits for you: " and the parts. No entry and nothing held: nothing is printed.

--skip <id>: leaves out the entries of that id (the queue item the same message posts); a key of
that id is neither added nor removed.

--new: after the line, one line "new: <entry>" for each entry whose key was not recorded before
this call. A held decision is never a "new:" line.

The keys: status/data/waits.json (a render, git-ignored by the status/data/* line of .gitignore)
holds {"keys": [...]}, the keys of the entries the last call printed: "E3 planned", "D14 ready",
"D14 hold over", "05-04 look", "<label> owner" for a milestone, "Q18". An entry that is no longer
in the list loses its key, so a thing that waits a second time is new again. "Held:" has no key.
The file is read back after the write.

--held: prints "Held:" and one line per held decision, "- D<n> <title>", with ": until <id>" or
": <the reason in words>" when there is one; nothing when no decision is held. Reads and writes
no key.

A release below format 2.2 (no dashboard data): every form prints nothing, writes nothing and
exits 0.
"""
import argparse
import importlib.util
import json
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
KEYS_FILE = "status/data/waits.json"
SEP = " · "
KIND_ORDER = ("epic", "decision", "task", "milestone", "queue")  # the order of the entries in the line
OWNER_PREFIX = "owner:"  # stripped from a milestone reason in its entry
USAGE = "status/waits.py <release> [--new | --held] [--skip <id>] [--owner X] [--root PATH]"


def number_key(text):
    """The numbers in an id or a label, to sort by: "05-04" is (5, 4), "D14" is (14,)."""
    return tuple(int(x) for x in re.findall(r"\d+", text or ""))


def entries(folder, data, rows):
    """[(kind, row id, entry text, key)] of the rows that wait, in the order of the line, and the
    sorted D numbers of the held decisions (id, title, entry of the status file)."""
    dc = C.load("lib/decisions")
    st = C.load("lib/status")
    file_form = dc.file_form(folder)
    holds = st.decision_entries(folder) if file_form else {}
    statuses = dc.id_statuses(folder) if file_form else {}
    task_milestone = {t["id"]: t.get("milestone", "") for t in data.get("tasks", [])}
    out, held = [], []
    for r in rows:
        k, rid = r["kind"], r["id"]
        if k == "epic" and r["status"] == "blocked" and r["turn"] == "you":
            out.append((k, rid, f"{r['label']} planned: delegate", f"{rid} planned"))
        elif k == "decision":
            state = dc.hold_state(holds.get(rid), statuses) if file_form else ""
            if r["ready"] and state == "over":
                out.append((k, rid, f"{rid}: hold over, ready: compose", f"{rid} hold over"))
            elif r["ready"]:
                out.append((k, rid, f"{rid} ready: compose", f"{rid} ready"))
            elif state == "held" and r["status"] in dc.OPEN_WORDS:
                held.append((rid, r["title"], holds.get(rid) or {}))
        elif k == "task" and r["turn"] == "you":
            out.append((k, rid, f"{r['label']}: your look", f"{r['label']} look"))
        elif k == "queue" and r["turn"] == "you":
            out.append((k, rid, f"{rid}: record it", rid))
    waiting_tasks = {task_milestone.get(rid) for k, rid, _, _ in out if k == "task"}
    for r in rows:
        if r["kind"] == "milestone" and r["turn"] == "you" and r["id"] not in waiting_tasks:
            reason = r["reason"]
            if reason.lower().startswith(OWNER_PREFIX):
                reason = reason[len(OWNER_PREFIX):].strip()
            out.append(("milestone", r["id"], f"{r['label']}: {reason}", f"{r['label']} owner"))
    label = {r["id"]: r["label"] for r in rows}
    out.sort(key=lambda e: (KIND_ORDER.index(e[0]), number_key(label.get(e[1], e[1]))))
    held.sort(key=lambda h: number_key(h[0]))
    return out, held


def skipped(entry, skip, label):
    """True when --skip names the entry's row, by its id or its label (label: {row id: label})."""
    return skip is not None and skip in (entry[1], label.get(entry[1]))


def read_keys(path):
    """The recorded keys; an empty list when the file is missing or cannot be read (a render:
    the next write makes it again)."""
    try:
        got = json.loads(C.read(path)).get("keys")
    except (OSError, ValueError, AttributeError):
        return []
    return [k for k in got if isinstance(k, str)] if isinstance(got, list) else []


def write_keys(path, keys):
    """Write the keys and read them back: a file that does not hold them ends the script."""
    C.load("lib/status").write_json(path, json.dumps({"keys": keys}, indent=2, ensure_ascii=False) + "\n")
    if read_keys(path) != keys:
        C.die(f"{path} does not hold the keys just written: delete it and run the call again")


def held_block(held):
    """The lines of --held."""
    lines = ["Held:"] if held else []
    dc = C.load("lib/decisions")
    for rid, title, entry in held:
        until = dc.hold_target(entry.get("hold"))
        why = f"until {until}" if until else entry.get("hold_reason", "")
        lines.append(f"- {rid} {title}" + (f": {why}" if why else ""))
    return lines


def main():
    ap = argparse.ArgumentParser(usage=USAGE)
    ap.add_argument("release")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--new", action="store_true", help="also print each entry that was not in the last list")
    mode.add_argument("--held", action="store_true", help="print each held decision with its reason")
    ap.add_argument("--skip", help="leave out the entries of this id, like Q19")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    if a.held and a.skip is not None:
        C.die("--held takes no --skip: the held block names every held decision")
    _, folder = C.find_folder(a.release, a.owner, a.root)
    dash = C.load("lib/dashboard")
    if not dash.applies(folder):
        return  # below format 2.2: no dashboard data, no line
    st = C.load("lib/status")
    data = st.stored(st.load(folder))
    built = dash.build(folder)
    found, held = entries(folder, data, built["rows"])
    if a.held:
        for line in held_block(held):
            print(line)
        return
    label = {r["id"]: r["label"] for r in built["rows"]}
    shown = [e for e in found if not skipped(e, a.skip, label)]
    keys_path = folder / KEYS_FILE
    before = read_keys(keys_path)
    parts = [e[2] for e in shown] + ([f"Held: {', '.join(h[0] for h in held)}"] if held else [])
    if parts:
        print("Waits for you: " + SEP.join(parts))
    if a.new:
        for e in shown:
            if e[3] not in before:
                print(f"new: {e[2]}")
    skip_keys = {e[3] for e in found if skipped(e, a.skip, label)}
    keys = [e[3] for e in shown] + [k for k in before if k in skip_keys]
    if keys != before or not keys_path.is_file():
        write_keys(keys_path, keys)


if __name__ == "__main__":
    main()
