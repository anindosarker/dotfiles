#!/usr/bin/env python3
"""status/data/status.json: the only store of the status of every epic, spec, milestone and
task of a release, and the data of the status page. Library for status/status.py,
sprints/mark.py, lib/grid.py and the readers; no CLI.

A release that has the file is read through it. A release without it (made before this format)
is read as before: grid marks, tracker "Status:" lines. plan/new_cycle.py writes the first file.

Five words (STATUSES): "not started", "in progress", "blocked", "done", "skipped". A blocked or
skipped item carries a short reason. Stored: the status, reason, changed time and merge commit
of each milestone, and the status, reason and changed time of each task. Counted on every
write (rollup): the status of a spec, an epic and a sprint, from the milestones inside.
Everything else in the file is rebuilt from the specs on every write (build), in the shape of
the status board: release, updated, root, statuses, sprints, epics, specs, milestones, tasks.

Ids: a milestone is its tracker file name without "-tracker.md" ("27-collapse-shortcut"), a
task is "<spec>-<number>" ("27-03"), a spec its number, an epic "E11".

set_status changes one milestone or task, then runs the chain: the roll-up of a task into its
milestone, the JSON file, the grid (lib/grid.py refresh, which draws status/sprints.md from this
file and ends in sync), status.data.js, and the "status:" front matter line of every task, spec
and epic file (mirror). Nobody writes a status by hand.
- A task set to done with an open "Owner:" box in its Verification list becomes blocked with
  the reason OWNER_REASON; with any other open box the change is refused.
- A task change rolls up into its milestone while the milestone is not done or skipped: in
  progress when a task is in work or some are finished, blocked when none is in work and one is
  blocked. A milestone becomes done only by its merge (sprints/mark.py merge, with the commit).
"""
import datetime
import importlib.util
import json
import re
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
FILE = "status/data/status.json"
SCRIPT = "status/data/status.data.js"
STATUSES = ("not started", "in progress", "blocked", "done", "skipped")
WITH_REASON = ("blocked", "skipped")
CLOSED = ("done", "skipped")
MARKS = {"not started": "·", "in progress": "[ ]", "blocked": "[~]", "done": "[x]", "skipped": "[!]"}
OWNER_REASON = "waits for the owner's look"
BOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(.*)$")
CHANGED = []


def own():
    return C.load("lib/ownership")


def path(folder):
    return folder / FILE


def active(folder):
    """True for a release whose statuses are in status.json."""
    return path(folder).is_file()


def load(folder):
    return json.loads(C.read(path(folder))) if active(folder) else None


def entries(folder):
    """({milestone id: entry}, {task id: entry}) of the stored file."""
    data = load(folder) or {}
    return ({m["id"]: m for m in data.get("milestones", [])}, {t["id"]: t for t in data.get("tasks", [])})


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def rollup(words):
    """One status from the statuses inside."""
    words = list(words)
    if not words:
        return STATUSES[0]
    if all(w in CLOSED for w in words):
        return "skipped" if all(w == "skipped" for w in words) else "done"
    if "in progress" in words:
        return "in progress"
    if "blocked" in words:
        return "blocked"
    return "in progress" if any(w in CLOSED for w in words) else STATUSES[0]


def old_state(folder, stem):
    """The stored status of the milestone with tracker name stem, as lib/ownership.py
    tracker_status gives a tracker's Status line: (planned | running | done | stopped, detail)."""
    m = entries(folder)[0].get(stem)
    word = m["status"] if m else STATUSES[0]
    if word == "done":
        return "done", m.get("commit", "")
    if word == "skipped":
        return "stopped", m.get("reason", "")
    return ("planned" if word == STATUSES[0] else "running"), ""


def boxes(task_file):
    """(open "Owner:" boxes, other open boxes) of the Verification list of a task file."""
    owner = other = 0
    inside = False
    for _, line in C.outside_fences(C.read(task_file)):
        if line.startswith("## "):
            inside = line.strip() == "## Verification"
        m = BOX_RE.match(line) if inside else None
        if m and m.group(1) == " ":
            if m.group(2).startswith("Owner:"):
                owner += 1
            else:
                other += 1
    return owner, other


def keep(old, with_commit=False):
    out = {"status": old.get("status", STATUSES[0]) if old.get("status") in STATUSES else STATUSES[0],
           "reason": old.get("reason", ""), "changed": old.get("changed", "")}
    if with_commit:
        out["commit"] = old.get("commit", "")
    return out


def build(folder, release, stored=None):
    """The whole file as a dict, from the specs, the grid columns and the stored entries."""
    o = own()
    old_m, old_t = stored or entries(folder)
    plan = folder / f"{release}-plan.md"
    comp = o.compute(folder)
    if comp["errors"]:
        o.print_errors(comp["errors"], "status.json not written")
    coll = o.new_collect(folder, plan)
    titles = o.spec_titles(plan)
    links = dict(coll["rows"])
    scope = {m.group(1): m.group(5) for m in C.load("sprints/swimlanes").PLAN_ROW_RE.finditer(
        C.read(plan) if plan.is_file() else "")}
    gcols = o.grid_columns(folder)
    by_name = {m["name"]: m for m in comp["milestones"]}
    stem = {b["name"]: b["tracker"].name.removesuffix("-tracker.md")
            for bl in coll["blocks"].values() for b in bl}
    epic_of = {num: o.spec_epic(p) for num, p in coll["docs"]}
    milestones, tasks = [], []

    def task_entry(num, t, mid):
        tid = f"{num}-{t['id']}"
        has_file = bool(t["path"] and t["path"].is_file())
        e = {"id": tid, "milestone": mid, "spec": num, "number": t["id"],
             "title": t["title"] if t["path"] else re.sub(r"^-\s*Task\s+\d+:\s*", "", t["title"])}
        e.update(keep(old_t.get(tid, {})))
        kind = o.front_matter(C.read(t["path"])).get("type", "") if has_file else ""
        e.update(ownerCheck=e["status"] == "blocked" and e["reason"] == OWNER_REASON,
                 type=kind if kind in ("feat", "bug") else "feat", decision=t["decision"] or "",
                 file=t["path"].relative_to(folder).as_posix() if has_file else "")
        return e

    for num, p in coll["docs"]:
        placed = set()
        epic = f"E{epic_of[num]}" if epic_of.get(num) else ""
        for b in coll["blocks"][num]:
            mid = stem[b["name"]]
            m = by_name.get(b["name"], {})
            col = gcols.get(b["name"])
            e = {"id": mid, "name": b["name"], "epic": epic, "spec": num, "sprint": f"S{col}" if col else ""}
            e.update(keep(old_m.get(mid, {}), with_commit=True))
            e.update(critical=b["name"] in comp["paths"].get(epic_of.get(num), []),
                     depends=[stem[d] for d in m.get("deps", []) if d in stem],
                     outcome=scope.get(num, ""), files=m.get("files", []))
            milestones.append(e)
            for t in b["tasks"]:
                placed.add(t["id"])
                tasks.append(task_entry(num, t, mid))
        for t in o.read_spec(p)["tasks"].values():
            if t["id"] not in placed:
                tasks.append(task_entry(num, t, ""))
    specs = []
    for num, p in coll["docs"]:
        inside = [m["status"] for m in milestones if m["spec"] == num] \
            or [t["status"] for t in tasks if t["spec"] == num]
        specs.append({"id": num, "title": titles.get(num, ""), "path": links[num],
                      "epic": f"E{epic_of[num]}" if epic_of.get(num) else "", "status": rollup(inside)})
    epics = []
    for n in o.epic_numbers(folder):
        mine = [s for s in specs if s["epic"] == f"E{n}"]
        head = re.search(rf"^# E{n}:?[ \t]+(\S.*?)[ \t]*$", C.read(o.epic_path(folder, n)), re.M)
        epics.append({"id": f"E{n}", "name": head.group(1) if head else (mine[0]["title"] if mine else ""),
                      "status": rollup(m["status"] for m in milestones if m["epic"] == f"E{n}"),
                      "specs": [s["id"] for s in mine]})
    sprints = []
    for c in sorted({int(m["sprint"][1:]) for m in milestones if m["sprint"]}):
        inside = [m["status"] for m in milestones if m["sprint"] == f"S{c}"]
        sprints.append({"id": f"S{c}", "status": rollup(inside),
                        "done": sum(1 for w in inside if w in CLOSED), "total": len(inside)})
    return {"release": release, "updated": now(), "root": str(folder), "statuses": list(STATUSES),
            "sprints": sprints, "epics": epics, "specs": specs, "milestones": milestones, "tasks": tasks}


def save(folder, data):
    """Write status.json and status.data.js when anything but the time changed."""
    p = path(folder)
    old = load(folder)
    if old is not None and {**old, "updated": ""} == {**data, "updated": ""}:
        data = old
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        CHANGED.append(p)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    (folder / SCRIPT).write_text(f"window.STATUS_DATA = {text};\n", encoding="utf-8")


def mirror(folder, data):
    """The "status:" front matter line of every task, spec and epic file, from data."""
    o = own()
    want = [(folder / t["file"], t["status"]) for t in data["tasks"] if t["file"]]
    want += [(folder / s["path"], s["status"]) for s in data["specs"]]
    want += [(o.epic_path(folder, int(e["id"][1:])), e["status"]) for e in data["epics"]]
    for p, word in want:
        if p.is_file():
            text = C.read(p)
            if o.front_matter(text).get("status") != word:
                p.write_text(o.set_front(text, "status", word, first=True), encoding="utf-8")
                CHANGED.append(p)


def differences(folder):
    """[(file, its status line, the stored status)] of each front matter line that differs from
    status.json: a status edited by hand."""
    o = own()
    data = load(folder) or {}
    want = [(folder / t["file"], t["status"]) for t in data.get("tasks", []) if t["file"]]
    want += [(folder / s["path"], s["status"]) for s in data.get("specs", [])]
    want += [(o.epic_path(folder, int(e["id"][1:])), e["status"]) for e in data.get("epics", [])]
    out = []
    for p, word in want:
        have = o.front_matter(C.read(p)).get("status") if p.is_file() else None
        if p.is_file() and have != word:
            out.append((p, have, word))
    return out


def sync(folder, release, stored=None):
    """Rebuild and write the file and the mirrors; the last step of lib/grid.py refresh."""
    data = build(folder, release, stored)
    save(folder, data)
    mirror(folder, data)
    return data


def changed():
    """The files written since the last call, for the caller's commit."""
    out = list(dict.fromkeys(CHANGED))
    CHANGED.clear()
    return out


def find(data, ident):
    """("milestone" | "task" | "spec" | "epic", entry) of an id, or (None, None)."""
    for kind in ("milestones", "tasks", "specs", "epics"):
        for e in data[kind]:
            if e["id"] == ident:
                return kind[:-1], e
    return None, None


def set_status(folder, release, ident, status, reason="", commit="", locked=False):
    """Set one milestone or task and run the chain. Returns (kind, entry, the word stored).
    Dies on an unknown id, a spec or an epic, a word that is not one of the five, a missing
    reason, or a task set to done with an open box that is not an "Owner:" line."""
    if status not in STATUSES:
        C.die(f"bad status '{status}': one of {', '.join(STATUSES)}")
    data = build(folder, release)
    kind, e = find(data, ident)
    if kind is None:
        C.die(f"no milestone or task has the id {ident}")
    if kind in ("spec", "epic"):
        C.die(f"the status of {kind} {ident} is counted from its milestones, never set")
    reason = reason.strip()
    if kind == "task" and status == "done" and e["file"]:
        owner, other = boxes(folder / e["file"])
        if other:
            C.die(f"task {ident} has {other} open Verification box(es): tick them first")
        if owner:
            status, reason = "blocked", OWNER_REASON
    if status in WITH_REASON and not reason:
        C.die(f'{status} needs --reason "<text>"')
    e.update(status=status, reason=reason if status in WITH_REASON else "", changed=now())
    if kind == "milestone":
        e["commit"] = commit if status == "done" else ""
    elif e["milestone"]:
        m = find(data, e["milestone"])[1]
        mine = [t for t in data["tasks"] if t["milestone"] == m["id"]]
        words = [t["status"] for t in mine]
        if m["status"] not in CLOSED and any(w != STATUSES[0] for w in words):
            word = rollup(words)
            word = "in progress" if word in CLOSED else word
            why = next((t["reason"] for t in mine if t["status"] == "blocked"), "") if word == "blocked" else ""
            if (m["status"], m["reason"]) != (word, why):
                m.update(status=word, reason=why, changed=now())
    p = path(folder)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    CHANGED.append(p)
    C.load("lib/grid").refresh(folder, release, quiet=True, locked=locked)
    if (folder / C.SPRINTS_MD).is_file():
        C.load("sprints/swimlanes").write(folder, release, quiet=True)
    return kind, e, status
