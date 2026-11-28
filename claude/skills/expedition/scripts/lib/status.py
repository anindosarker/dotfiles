#!/usr/bin/env python3
"""status/data/status.json: the only store of the status of every epic, spec, milestone and
task of a release, and the data of the status page. Library for status/status.py,
sprints/mark.py, lib/grid.py and the readers; no CLI.

A release that has the file is read through it. A release without it (made before this format)
is read as before: grid marks, tracker "Status:" lines. plan/new_release.py writes the first file.

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
file and ends in sync), status.data.js (and, for a release of format 2.1, queue.data.js, the
queue data of the page, lib/queue.py), and the "status:" front matter line of every task, spec
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
import os
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
NEW_FORMAT = (2, 2)
# Format 2.2 (spec 04, D11): the stored and printed words. The code keeps the words of STATUSES.
WORDS_22 = {"not started": "to-do", "skipped": "archived"}
PENDING = "status/data/.pending"
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
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
    """The stored file as a dict; None for a release without it. A file that cannot be parsed
    ends the script with one line."""
    if not active(folder):
        return None
    try:
        data = json.loads(C.read(path(folder)))
    except ValueError as e:
        C.die(f"{path(folder)} is not valid JSON ({e}): restore it from git; no status was changed")
    if not (isinstance(data, dict) and isinstance(data.get("milestones"), list) and isinstance(data.get("tasks"), list)):
        C.die(f"{path(folder)} has no milestone and task lists: restore it from git; no status was changed")
    return data


def write_json(p, text):
    """Write text to p through a temporary file, so a reader never sees half a file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def release_format(folder):
    """The format a release is in: the "format" key of its status file; "1.0" with no file."""
    return (load(folder) or {}).get("format") or "1.0"


def version(text):
    """A format or version string as a tuple to compare: "2.2" is (2, 2)."""
    return tuple(int(x) for x in re.findall(r"\d+", text or "")) or (1, 0)


def say(folder, word):
    """The word a release stores and prints for the word of the code (STATUSES): in a release of
    format 2.2 "to-do" for "not started" and "archived" for "skipped" (WORDS_22)."""
    return WORDS_22.get(word, word) if new_form(folder) else word


def new_form(folder):
    """True for a release of format 2.2 or higher (spec 04): the words of WORDS_22 and the epic
    file with its Ownership table as the one copy of its decisions and specs. The skill's own
    version plays no part."""
    return version(release_format(folder)) >= NEW_FORMAT


def entries(folder):
    """({milestone id: entry}, {task id: entry}) of the stored file."""
    data = load(folder) or {}
    return ({m["id"]: m for m in data.get("milestones", [])}, {t["id"]: t for t in data.get("tasks", [])})


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def rollup(words):
    """One status from the statuses inside. skipped is closed, never started: with only skipped
    and not started items nothing has started."""
    words = list(words)
    if not words:
        return STATUSES[0]
    if all(w in CLOSED for w in words):
        return "skipped" if all(w == "skipped" for w in words) else "done"
    if "in progress" in words:
        return "in progress"
    if "blocked" in words:
        return "blocked"
    return "in progress" if "done" in words else STATUSES[0]


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
        for k, b in enumerate(coll["blocks"][num], 1):
            mid = stem[b["name"]]
            m = by_name.get(b["name"], {})
            col = gcols.get(b["name"])
            n = int(b["id"].rsplit(".", 1)[1]) if b["id"] else k
            e = {"id": mid, "name": b["name"], "number": n, "section": b["id"] or f"2.2.{n}", "ref": f"{num}.{n}",
                 "epic": epic, "spec": num, "sprint": f"S{col}" if col else ""}
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
    have = {e["id"] for e in milestones + tasks}
    lost = sorted(i for i, e in {**old_m, **old_t}.items()
                  if i not in have and (e.get("status", STATUSES[0]) != STATUSES[0] or e.get("changed")))
    if lost:
        C.die(f"status.json holds statuses no spec has now: {', '.join(lost)}. A spec lost its row or link in "
              "the Deliverables table, or a milestone or task was renamed or removed: restore it, or drop "
              f"each entry with status/status.py {release} drop <id>. Nothing written")
    specs = []
    for num, p in coll["docs"]:
        mine = [m["status"] for m in milestones if m["spec"] == num]
        inside = mine + [t["status"] for t in tasks if t["spec"] == num] if mine else []
        specs.append({"id": num, "title": titles.get(num, ""), "path": links[num],
                      "epic": f"E{epic_of[num]}" if epic_of.get(num) else "", "status": rollup(inside)})
    epics = []
    for n in o.epic_numbers(folder):
        mine = [s for s in specs if s["epic"] == f"E{n}"]
        head = re.search(rf"^# E{n}:?[ \t]+(\S.*?)[ \t]*$", C.read(o.epic_path(folder, n)), re.M)
        epics.append({"id": f"E{n}", "name": head.group(1) if head else (mine[0]["title"] if mine else ""),
                      "status": rollup(s["status"] for s in mine),
                      "specs": [s["id"] for s in mine]})
    sprints = []
    for c in sorted({int(m["sprint"][1:]) for m in milestones if m["sprint"]}):
        inside = [m["status"] for m in milestones if m["sprint"] == f"S{c}"]
        sprints.append({"id": f"S{c}", "status": rollup(inside),
                        "done": sum(1 for w in inside if w in CLOSED), "total": len(inside)})
    return {"release": release, "format": (load(folder) or {}).get("format") or C.skill_version(),
            "updated": now(), "statuses": list(STATUSES),
            "sprints": sprints, "epics": epics, "specs": specs, "milestones": milestones, "tasks": tasks}


def save(folder, data):
    """Write status.json when anything but the time changed, and status.data.js, the same data
    with "root", the release folder on this machine (a render, git-ignored)."""
    p = path(folder)
    old = load(folder)
    if old is not None and {**old, "updated": ""} == {**data, "updated": ""}:
        data = old
    else:
        write_json(p, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        CHANGED.append(p)
    write_page_data(folder, data)


def write_page_data(folder, data=None):
    """status.data.js, the data of the page status/index.html: the stored file plus "root". For a
    release of format 2.1 also queue.data.js, the data of its Queue view (lib/queue.py)."""
    data = data or load(folder)
    page = {k: v for k, v in data.items() if k in ("release", "format", "updated")}
    page.update(root=str(folder), **{k: v for k, v in data.items() if k not in page})
    write_json(folder / SCRIPT, f"window.STATUS_DATA = {json.dumps(page, indent=2, ensure_ascii=False)};\n")
    C.load("lib/queue").write_data(folder)


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


def commit(root, folder, extra, message):
    """Commit the files the store and its mirrors wrote, with extra. The paths are kept in
    status/data/.pending (git-ignored) until a commit succeeds, so a run after a failed commit
    still commits every mirrored file. Returns what lib/common.py commit returns."""
    pend = folder / PENDING
    kept = [folder / l for l in C.read(pend).splitlines() if l.strip()] if pend.is_file() else []
    paths = list(dict.fromkeys(kept + CHANGED + [Path(p) for p in extra]))
    CHANGED.clear()
    if not paths:
        return False
    pend.parent.mkdir(parents=True, exist_ok=True)
    pend.write_text("".join(f"{p.relative_to(folder).as_posix()}\n" for p in paths), encoding="utf-8")
    done = C.commit(root, [str(p) for p in paths], message)
    pend.unlink()
    return done


def pending(folder):
    """True when a commit failed before: its paths wait in status/data/.pending."""
    return (folder / PENDING).is_file()


def drop(folder, release, ident):
    """Remove one stored milestone or task entry that no spec has. Returns its kind, or None
    when the file has no such entry. Dies when a spec still has the milestone or task."""
    o = own()
    live = set()
    for num, bl in o.new_collect(folder, folder / f"{release}-plan.md")["blocks"].items():
        for b in bl:
            live.add(b["tracker"].name.removesuffix("-tracker.md"))
    for num, p in o.spec_files(folder):
        doc = o.read_spec(p)
        live |= {f"{num}-{t}" for t in doc["tasks"]} | {f"{num}-{t['id']}" for b in doc["blocks"] for t in b["tasks"]}
    if ident in live:
        C.die(f"{ident} is a milestone or task a spec still has: drop removes only an entry no spec has")
    data = load(folder)
    for kind in ("milestones", "tasks"):
        left = [e for e in data[kind] if e["id"] != ident]
        if len(left) != len(data[kind]):
            data[kind] = left
            write_json(path(folder), json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            CHANGED.append(path(folder))
            return kind[:-1]
    return None


def find(data, ident):
    """("milestone" | "task" | "spec" | "epic", entry) of an id, or (None, None)."""
    for kind in ("milestones", "tasks", "specs", "epics"):
        for e in data[kind]:
            if e["id"] == ident:
                return kind[:-1], e
    return None, None


def set_status(folder, release, ident, status, reason="", commit="", locked=False, boxes_in=None):
    """Set one milestone or task and run the chain. Returns (kind, entry, the word stored), the
    word None when nothing changed (then nothing is written). Dies on an unknown id, a spec or
    an epic, a word that is not one of the five, a missing reason, a task set to done with an
    open box that is not an "Owner:" line, a milestone set to done without a commit hash or
    with a task that is not finished."""
    if status not in STATUSES:
        C.die(f"bad status '{status}': one of {', '.join(STATUSES)}")
    data = build(folder, release)
    kind, e = find(data, ident)
    if kind is None:
        C.die(f"no milestone or task has the id {ident}")
    if kind in ("spec", "epic"):
        C.die(f"the status of {kind} {ident} is counted from what is inside it, never set")
    reason = reason.strip()
    if kind == "task" and status == "done" and e["file"]:
        mine_copy = (boxes_in or folder) / e["file"]  # the builder ticks the boxes in its own copy
        owner, other = boxes(mine_copy if mine_copy.is_file() else folder / e["file"])
        if other:
            C.die(f"task {ident} has {other} open Verification box(es): tick them first")
        if owner:
            status, reason = "blocked", OWNER_REASON
    if status in WITH_REASON and not reason:
        C.die(f'{status} needs --reason "<text>"')
    mine = [t for t in data["tasks"] if t["milestone"] == (ident if kind == "milestone" else e["milestone"])]
    if kind == "milestone" and status == "done":
        if not COMMIT_RE.match(commit):
            C.die(f"milestone {ident}: done is its merge and needs --commit <sha>, 7 to 40 hex characters")
        open_ = [t["number"] for t in mine if not (t["status"] in CLOSED or t["ownerCheck"])]
        if open_:
            C.die(f"milestone {ident} cannot merge: task(s) {', '.join(open_)} are not done, skipped or "
                  "waiting for the owner's look")
    new = {"status": status, "reason": reason if status in WITH_REASON else ""}
    if kind == "milestone":
        new["commit"] = commit if status == "done" else ""
    if all(e[k] == v for k, v in new.items()):
        return kind, e, None
    e.update(new, changed=now())
    if kind == "task":
        e["ownerCheck"] = status == "blocked" and reason == OWNER_REASON
        m = find(data, e["milestone"])[1] if e["milestone"] else None
        words = [t["status"] for t in mine]
        if m and m["status"] not in CLOSED and any(w not in (STATUSES[0], "skipped") for w in words):
            word = rollup(words)
            word = "in progress" if word in CLOSED else word
            why = next((t["reason"] for t in mine if t["status"] == "blocked"), "") if word == "blocked" else ""
            if (m["status"], m["reason"]) != (word, why):
                m.update(status=word, reason=why, changed=now())
    write_json(path(folder), json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    CHANGED.append(path(folder))
    C.load("lib/grid").refresh(folder, release, quiet=True, locked=locked)
    if (folder / C.SPRINTS_MD).is_file():
        C.load("sprints/swimlanes").write(folder, release, quiet=True)
    return kind, e, status
