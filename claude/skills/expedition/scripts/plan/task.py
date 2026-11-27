#!/usr/bin/env python3
"""Add a task to a spec, and set the status of a task. The only writer of task status.

Usage: python3 -I plan/task.py add <release> <spec> "<Title>" [--decision D<n>] [--cites "Q3, Q4"]
           [--checks "<checks>"] [--milestone "<name>"] [--file | --no-file] [--type feat]
           [--remark "<the owner's words>"] [--owner X] [--root PATH]
       python3 -I plan/task.py status <release> <spec> <task id> "<status>" [--reason "<text>"]
       python3 -I plan/task.py start <release> <spec> <task id>     (status "in progress")
       python3 -I plan/task.py done <release> <spec> <task id>      (status "done")

add, for a spec in the new form (a "2.1 Tasks" and a "2.2 Milestones" section):
- writes "#### 2.1.N Task: <Title> (<ids>)" at the end of 2.1 Tasks, with "- Checks:" when
  --checks is given and "- Plan: tasks/NN-<slug>.md" when it has a task file;
- adds the id to the "- Tasks:" line of an open milestone (a grid cell that is not "[x]"):
  --milestone, else the spec's last open one. No open milestone is refused: plan/milestone.py
  add opens one;
- creates the task file from templates/task.md, "status: not started", the remark quoted in its
  Description: by default in an iterative spec, with --file in a structured one, never with
  --no-file. A task with no file gets its line in the milestone's tracker task list;
- with --decision, while the spec is in an epic, adds the decision to that epic as
  plan/milestone.py does; each --cites card moves to Autofix.
Commits the spec, the task file, the tracker and the files the decision changed.

status: one of "not started", "in progress", "blocked", "done" (lib/specs.py STATUSES).
"blocked" needs --reason; any other status removes the reason. The status is written into the
task file's front matter ("status:", and "blocked: <reason>") when the task has a task file,
else into the task list of its milestone's tracker; lib/specs.py reads both the same way. It
writes the copy in the main checkout (the first entry of git worktree list), so the status page
shows it at once, rewrites the page data (sprints/swimlanes.py) and commits the one file.
Milestone status is not touched: that is sprints/mark.py.

Refuses, writing nothing: an old-form or closed spec (add); a D id among --cites; a decision
not in decisions.md, superseded or in another epic; an unknown milestone or task id; a status
that is not one of the four; "blocked" with no reason.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
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
NUM_RE = re.compile(r"^\d{2}(?:\.\d+)?$")
CITES_RE = re.compile(r"^Q\d+(\s*,\s*Q\d+)*$")
D_RE = re.compile(r"^D(\d+)$")
SHORT = {"start": "in progress", "done": "done"}
die, load = C.die, C.load


def task_file_text(task_id, title, kind, decision, remark):
    path = C.TEMPLATES / "task.md"
    if not path.is_file():
        die(f"bundled template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("task:"):
            line = f"task: {task_id}"
        elif line.startswith("type:"):
            line = f"type: {kind}"
        elif line.startswith("decision:"):
            if decision is None:
                continue
            line = f"decision: D{decision}"
        elif line.startswith("# "):
            line = f"# {title}"
        elif line.startswith("> ") and remark:
            line = f"> {remark}"
        out.append(line)
    return "\n".join(out) + "\n"


def add(a, own, sp, root, folder, lock):
    if len(a.rest) != 1:
        die('add takes <release> <spec> "<Title>"')
    title = a.rest[0]
    for label, val in (("title", title), ("checks", a.checks), ("remark", a.remark)):
        if "—" in val:
            die(f"{label} contains an em dash")
    ids = []
    if a.cites.strip():
        if not CITES_RE.match(a.cites.strip()):
            die(f"bad ids '{a.cites}', expected like \"Q3, Q4\" (a decision goes in --decision)")
        ids = [s.strip() for s in a.cites.split(",")]
    decision = None
    if a.decision:
        m = D_RE.match(a.decision)
        if not m:
            die(f"bad decision '{a.decision}', expected like D58")
        decision = int(m.group(1))
    bd = load("lib/board")
    fcntl.flock(lock, fcntl.LOCK_EX)
    queue = folder / own.QUEUE_MD
    have = {c["num"] for c in bd.parse(own.read(queue))["cards"]} if queue.is_file() else set()
    missing = [i for i in ids if int(i[1:]) not in have]
    if missing:
        die(f"not in {queue.name}: {', '.join(missing)}")
    path = dict(own.spec_files(folder)).get(a.spec)
    if path is None:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    text = own.read(path)
    if not sp.new_form(text):
        die(f"spec {a.spec} is in the old form: write its Task line by hand")
    doc, trackers = sp.spec_trackers(folder, a.spec, path)
    if doc["closed"]:
        die(f"spec {a.spec} is closed ({doc['closed']}): new work needs a new spec")
    epic = own.spec_epic(path)
    if decision is not None:
        sp.check_decision(folder, decision, epic)
    cells = sp.grid_cells(folder, a.spec)
    names = [b["name"] for b in doc["blocks"]]
    if a.milestone and a.milestone not in names:
        die(f"spec {a.spec} has no milestone '{a.milestone}'")
    open_ = [n for n in names if cells.get(n) != "[x]" and a.milestone in (None, n)]
    if not open_:
        die(f"spec {a.spec} has no open milestone" + (f" named '{a.milestone}'" if a.milestone else "")
            + ": open one with plan/milestone.py add")
    milestone = open_[-1]
    with_file = a.file if a.file is not None else doc["type"] == "iterative"
    name_of = lambda tid: f"tasks/{int(tid.rsplit('.', 1)[1]):02d}-{C.slugify(title)}.md"
    cites = ([f"D{decision}"] if decision is not None else []) + ids
    text, tid = sp.add_task(text, list(doc["tasks"]), title, cites, a.checks or None,
                            name_of if with_file else None)
    writes = {path: sp.link_task(text, milestone, tid)}
    if with_file:
        if path.parent.name != path.stem:
            die(f"spec {a.spec} is one flat file: a task file needs the spec folder {path.stem}/")
        out = path.parent / name_of(tid)
        if out.exists():
            die(f"refusing to overwrite {out}")
        writes[out] = task_file_text(tid, title, a.type, decision, a.remark)
    else:
        out = trackers[milestone]
        base = own.read(out) if out.is_file() else C.tracker_text(a.spec, milestone)
        writes[out] = sp.set_tracker_task(base, tid, title, sp.STATUSES[0])
    for p, t in writes.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    if ids:
        q_text = own.read(queue)
        for i in ids:
            q_text = bd.move(q_text, int(i[1:]), "Autofix")
        bd.write(queue, q_text)
    fcntl.flock(lock, fcntl.LOCK_UN)
    if decision is not None and epic:
        sp.tag_decision(folder, epic, decision)
    page(own, folder, a.release)
    fcntl.flock(lock, fcntl.LOCK_EX)
    paths = [str(p) for p in writes] + [str(folder / "decisions.md"), str(queue)]
    paths += [str(p) for p in sorted((folder / own.EPICS_DIR).glob("E*.md"))]
    C.commit(root, paths, f"docs(plan): {a.release} task {a.spec} {tid} {title}")
    fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"task {tid} of spec {a.spec}: '{title}' in milestone '{milestone}', "
          + (f"file {out.relative_to(folder).as_posix()}" if with_file else "no task file"))


def page(own, folder, release):
    """Rewrite the status page data, when the release has a grid."""
    if (folder / own.SPRINTS_MD).is_file():
        with contextlib.redirect_stdout(io.StringIO()):
            load("sprints/swimlanes").write(folder, release, quiet=True)


def status(a, own, sp, root, folder, lock):
    want = 1 if a.action in SHORT else 2
    if len(a.rest) != want:
        die(f"{a.action} takes <release> <spec> <task id>" + (' "<status>"' if want == 2 else ""))
    tid = a.rest[0]
    value = SHORT.get(a.action) or a.rest[1].strip().lower()
    if value not in sp.STATUSES:
        die(f"bad status '{value}': one of {', '.join(sp.STATUSES)}")
    if value in sp.WITH_REASON and not a.reason.strip():
        die(f'{value} needs --reason "<text>"')
    path = dict(own.spec_files(folder)).get(a.spec)
    if path is None:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    doc, trackers = sp.spec_trackers(folder, a.spec, path)
    task = doc["tasks"].get(tid)
    if task is None:
        die(f"spec {a.spec} has no task {tid}")
    tracker = next((trackers[b["name"]] for b in doc["blocks"] if task in b["tasks"]), None)
    if tracker is None and not sp.has_file(task):
        die(f"task {tid} is in no milestone and has no task file: nowhere to keep its status")
    fcntl.flock(lock, fcntl.LOCK_EX)
    out = sp.set_task_status(task, tracker, value, a.reason.strip())
    page(own, folder, a.release)
    C.commit(root, [str(out)], f"docs(plan): {a.release} task {a.spec} {tid} {value}")
    fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"task {tid} of spec {a.spec}: {value} ({out.relative_to(folder).as_posix()})")


def main():
    ap = argparse.ArgumentParser(
        usage='plan/task.py add <release> <spec> "<Title>" [--decision D<n>] [--cites "Q3, Q4"] '
              '[--checks "<checks>"] [--milestone "<name>"] [--file | --no-file] [--type feat] '
              '[--remark "<text>"]\n       plan/task.py status <release> <spec> <task id> "<status>" '
              '[--reason "<text>"]\n       plan/task.py start|done <release> <spec> <task id>')
    ap.add_argument("action", choices=("add", "status", "start", "done"))
    ap.add_argument("release")
    ap.add_argument("spec")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--decision")
    ap.add_argument("--cites", default="")
    ap.add_argument("--checks", default="")
    ap.add_argument("--milestone")
    ap.add_argument("--file", dest="file", action="store_true", default=None)
    ap.add_argument("--no-file", dest="file", action="store_false")
    ap.add_argument("--type", default="feat")
    ap.add_argument("--remark", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    own, sp = load("lib/ownership"), load("lib/specs")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    if a.action != "add":
        main_root = load("status/progress").worktrees(root)[0][0]
        if main_root != root and (main_root / folder.relative_to(root)).is_dir():
            root, folder = main_root, main_root / folder.relative_to(root)
    with open(C.lock_file(folder), "a") as lock:
        (add if a.action == "add" else status)(a, own, sp, root, folder, lock)


if __name__ == "__main__":
    main()
