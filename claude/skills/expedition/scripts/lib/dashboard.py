#!/usr/bin/env python3
"""The data of the dashboard page of a release of format 2.2 (D14): status/data/dashboard.data.js
and status/data/dashboard.json. Library, no CLI. The contract is the page README, section Data
(board/README.md).

lib/queue.py write_data() calls write() after its blocked check, so the two files are written in
every step that writes status.data.js (lib/status.py write_page_data runs write_data) or
queue.data.js (the queue commands run write_data alone, after their commit). sprints/refresh.py
rebuilds them through the same step after a hand edit. A release below format 2.2 gets neither
file and no other change.

Both files are renders, git-ignored with the rest of status/data/; nobody edits them by hand.
dashboard.data.js is one line, "window.DASHBOARD_DATA = {...};", with release, updated, roots,
sources and rows. dashboard.json is the same data, indented, without roots: the file an agent
reads. roots.plan and roots.status are both the release folder on this machine.

One row per queue item (by number), per decision (with the board: per card of decisions.md, in
file order; in the file form: per decision file, in the order of the numbers), then per epic,
milestone and task (in the order of status/data/status.json). The fields of a row are FIELDS, in
that order; "decision" is on queue rows only, "progress" on epic rows only. A text field with no
value is "", ready is true or false. Where the values come from:
- queue: the item file (lib/queue.py). status and decider are the stored lines (the blocked check
  has stored "blocked" already); reason "Waits for <ids>" on a blocked item, the depends_on ids
  that are not done; depends_on and decision the lines as written; details the text under
  "## Details".
- decision, the file form (lib/decisions.py file_form, D9 and D16): the decision file. status
  and decider are its stored lines (decider "" when the file has none); reason on a blocked
  decision the words of lib/decisions.py blocked_reason ("Waits for E11, same file"), on every
  other its "epic" line ("E<n>", "" when none); file "decisions/D<n>-<slug>.md"; details the body
  of the file.
- decision, the board (a release of format 2.2 not yet moved by scripts/migrate/v2.1-v2.2): the
  card. status from its lane and tag (DECISION_STATUS; #deferred is backlog and #superseded
  archived in the lane Done); never blocked, decider ""; reason its epic "E<n>"; file
  decisions.md; details the lines of the card under its title.
- epic, milestone, task: status, reason and decider as stored in the status file; nothing is
  mapped and no decider is worked out again.
Worked out on every build and stored in no file: label, turn, ready, command, progress, root,
file (turn()).
"""
import datetime
import importlib.util
import json
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
SCRIPT = "status/data/dashboard.data.js"
JSON_FILE = "status/data/dashboard.json"
FIELDS = ("kind", "id", "label", "title", "status", "turn", "ready", "command", "depends_on", "decider",
          "decision", "reason", "progress", "root", "file", "details")
CLOSED = ("done", "archived", "backlog")  # no turn: nothing is left to move
FINISHED = ("done", "archived")  # the tasks an epic's progress counts as done
DECISION_STATUS = {"To do": "to-do", "In progress": "in progress", "Done": "done"}
OWNER_PREFIX = "owner:"  # a milestone reason that names the owner as the one to move
LEAD_PREFIX = "lead:"  # a milestone reason that names the lead as the one to move


def lib(name):
    return C.load(f"lib/{name}")


def applies(folder):
    """True for a release of format 2.2 or higher, the only one with dashboard data."""
    return lib("status").new_form(Path(folder))


def row(**values):
    """A row with the fields of FIELDS in that order; a field left out is "" (ready False), and
    "decision" and "progress" are kept only when given."""
    out = {}
    for k in FIELDS:
        if k in values:
            out[k] = values[k]
        elif k == "ready":
            out[k] = False
        elif k not in ("decision", "progress"):
            out[k] = ""
    return out


def turn(kind, status, reason="", owner_check=False):
    """Whose move an item is: "you", "lead", "agent", or "" for a closed item (README, Turn; D11
    for a planned epic)."""
    if status in CLOSED:
        return ""
    if kind == "queue":
        return "lead"  # a to-do item with options is "you": queue_rows() decides that case
    if kind == "decision":
        return "lead" if status == "to-do" else "agent"
    if kind == "epic":
        return "you" if status == "blocked" and reason == lib("status").DELEGATE_REASON else "agent"
    if status == "blocked":
        owner = lib("status").OWNER_REASON
        if kind == "milestone":
            if reason == owner or reason.lower().startswith(OWNER_PREFIX):
                return "you"
            if reason.lower().startswith(LEAD_PREFIX):
                return "lead"
        elif kind == "task" and (owner_check or reason == owner):
            return "you"
    return "agent"


def queue_rows(folder):
    Q = lib("queue")
    its = Q.items(folder)
    out = []
    for it in its:
        st = Q.status_of(it, True)
        waits = Q.waits_for(it, its) if st == "blocked" else []
        s = Q.sections(it["text"])
        who = turn("queue", st)
        if st == "to-do":
            who = "you" if "options" in s else "lead"
        out.append(row(kind="queue", id=f"Q{it['file_num']}", label=f"Q{it['file_num']}", title=it["title"],
                       status=st, turn=who, depends_on=Q.front(it["text"]).get("depends_on", ""),
                       decider=it["decider"], decision=it["decision"],
                       reason=f"Waits for {', '.join(waits)}" if waits else "",
                       root="plan", file=it["path"].relative_to(folder).as_posix(), details=s.get("details", "")))
    return out


def decision_rows(folder):
    D = lib("decisions")
    if D.file_form(folder):
        return file_decision_rows(folder)
    out = []
    for c in D.read_cards(folder)["cards"]:
        st = DECISION_STATUS.get(c["lane"])
        if st is None:
            continue  # a lane that is not one of the three: status/report.py names it
        if st == "done" and "superseded" in c["tags"]:
            st = "archived"
        elif st == "done" and "deferred" in c["tags"]:
            st = "backlog"
        epic = f"E{c['epic']}" if c["epic"] else ""
        ready = st == "to-do" and not epic
        out.append(row(kind="decision", id=f"D{c['num']}", label=f"D{c['num']}", title=c["title"], status=st,
                       turn=turn("decision", st), ready=ready, command="compose" if ready else "",
                       reason=epic, root="plan", file=D.DECISIONS_MD, details="\n".join(c["body"]).strip()))
    return out


def file_decision_rows(folder):
    """The decision rows of the file form: the stored status and decider of each file; the reason
    of a blocked decision from lib/decisions.py blocked_reason, else the epic line."""
    D = lib("decisions")
    cards = D.file_cards(folder)
    waits = D.status_and_waits(folder, cards)[1] if any(c["status"] == "blocked" for c in cards) else {}
    out = []
    for c in cards:
        st = c["status"]
        epic = f"E{c['epic']}" if c["epic"] else ""
        reason = D.blocked_reason(waits[c["num"]])[0] if st == "blocked" and c["num"] in waits else \
            "" if st == "blocked" else epic
        ready = st == "to-do" and not epic
        out.append(row(kind="decision", id=f"D{c['num']}", label=f"D{c['num']}", title=c["title"], status=st,
                       turn=turn("decision", st), ready=ready, command="compose" if ready else "",
                       decider=c["decider"], reason=reason, root="plan", file=c["file"],
                       details="\n".join(c["body"])))
    return out


def plan_rows(folder, data):
    """The epic, milestone and task rows from the stored status file, in its words."""
    o = lib("ownership")
    out = []
    for e in data.get("epics", []):
        mids = {m["id"] for m in data.get("milestones", []) if m.get("epic") == e["id"]}
        mine = [t for t in data.get("tasks", []) if t.get("milestone") in mids]
        n = int(e["id"][1:])
        out.append(row(kind="epic", id=e["id"], label=e["id"], title=e.get("name", ""), status=e["status"],
                       turn=turn("epic", e["status"], e.get("reason", "")), decider=e.get("decider", ""),
                       reason=e.get("reason", ""),
                       progress={"done": sum(1 for t in mine if t["status"] in FINISHED), "total": len(mine)},
                       root="status", file=f"{C.EPICS_DIR}/E{n}.md" if o.epic_path(folder, n).is_file() else ""))
    for m in data.get("milestones", []):
        out.append(row(kind="milestone", id=m["id"], label=m.get("ref") or m.get("spec", ""), title=m.get("name", ""),
                       status=m["status"], turn=turn("milestone", m["status"], m.get("reason", "")),
                       decider=m.get("decider", ""), reason=m.get("reason", ""), root="status"))
    for t in data.get("tasks", []):
        out.append(row(kind="task", id=t["id"], label=f"{t['spec']}-{t['number']}", title=t.get("title", ""),
                       status=t["status"], turn=turn("task", t["status"], t.get("reason", ""), t.get("ownerCheck")),
                       decider=t.get("decider", ""), reason=t.get("reason", ""), root="status",
                       file=t.get("file", "")))
    return out


def decision_source(folder):
    """The source of the decision rows: the folder "decisions/" in the file form, else decisions.md."""
    D = lib("decisions")
    return f"{D.DECISIONS_DIR}/" if D.file_form(folder) else D.DECISIONS_MD


def build(folder):
    """The data of the two files, with roots, for a release of format 2.2; None below it."""
    folder = Path(folder)
    if not applies(folder):
        return None
    st = lib("status")
    data = st.stored(st.load(folder))
    items = sorted(p.relative_to(folder).as_posix() for p in lib("queue").item_files(folder).values())
    return {"release": data.get("release") or lib("queue").release_of(folder),
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "roots": {"plan": str(folder), "status": str(folder)},
            "sources": {"queue": items, "decisions": decision_source(folder), "status": st.FILE},
            "rows": queue_rows(folder) + decision_rows(folder) + plan_rows(folder, data)}


def write(folder):
    """Write the two files for a release of format 2.2; nothing below it. Returns the paths
    written ([] below 2.2). Each file is read back: a file that does not hold every row ends the
    script with one line."""
    folder = Path(folder)
    data = build(folder)
    if data is None:
        return []
    st = lib("status")
    plain = {k: v for k, v in data.items() if k != "roots"}
    js, jf = folder / SCRIPT, folder / JSON_FILE
    st.write_json(js, f"window.DASHBOARD_DATA = {json.dumps(data, ensure_ascii=False)};\n")
    st.write_json(jf, json.dumps(plain, indent=2, ensure_ascii=False) + "\n")
    want = len(data["rows"])
    try:
        got_js = len(json.loads(C.read(js).strip()[len("window.DASHBOARD_DATA = "):-1])["rows"])
        got_jf = len(json.loads(C.read(jf))["rows"])
    except (ValueError, KeyError, TypeError) as e:
        C.die(f"{js} or {jf} could not be read back ({e}): run python3 -I scripts/sprints/refresh.py "
              f"{data['release']} to write them again")
    if got_js != want or got_jf != want:
        C.die(f"{js} or {jf} holds a different number of rows than the {want} built: run python3 -I "
              f"scripts/sprints/refresh.py {data['release']} to write them again")
    return [js, jf]
