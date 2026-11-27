#!/usr/bin/env python3
"""Add a milestone to a spec: a fix found during a run, a new round of an iterative spec, or
work for a decision that joins a spec after its epic's go.

Usage: python3 -I plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>]
       [--cites "Q3, Q4"] [--checks "<checks>"] [--files a,b] [--depends "<milestone names>"]
       [--owner X] [--root PATH]

<spec> is the spec the work belongs to. The milestone goes into that spec, also when every
milestone of it is merged: follow-up work is a new milestone, never a new spec file. The block
is written in the form the spec has:
- New form (a "2.1 Tasks" and a "2.2 Milestones" section): "#### 2.2.N Milestone: <Name>" with
  "- Tasks:", "- Files owned:" the --files when given, "- Depends on:" when a dependency exists,
  "- Review: none". With --decision, --cites or --checks it also writes the first task, named
  like the milestone, "#### 2.1.N Task: <Name> (<ids>)" with "- Checks: <checks>"; the task
  carries the cite. With none of the three, in an iterative spec only, the milestone is an
  empty round that plan/task.py add fills.
- Old form ("### Milestone:" blocks): "### Milestone: <Name>" with "- Files owned:",
  "- Depends on:", "- Review: none" and "- Task 1: <Name> (<ids>). Checks: <checks>"; --files
  and --checks are required.
Dependencies: every other milestone owning one of the --files, plus --depends. With neither, a
new-form milestone runs after the spec's previous one (no line is written).
While the spec is in an epic (an "- Epic: E<n>" line): the block gets "- Starts: S<n>", the
current sprint, so its row never lands in a finished sprint, and the name is added to the
Milestone cell of the spec's rows in the epic file. --decision then also adds the decision to
that epic (its "Decisions:" line, an Ownership row, the "#E<n>" tag, the card to In progress).
A spec in no epic yet gets the block only; the go tags it.
The tracker is run/trackers/NN-<name slug>-tracker.md, "Status: planned"; the first milestone
of a spec keeps the tracker plan/new_spec.py made.

Refuses, writing nothing: a D id among --cites (use --decision); a Q id not in queue.md; a
decision not in decisions.md, superseded, or tagged into another epic; a spec with no file; a
closed iterative spec; a milestone name already taken; milestones that no longer schedule
(sprints/check.py names the error). Then each cited card moves to the end of Autofix, ticked,
without tags, under the .ids.lock lock; the refresh chain (lib/grid.py refresh) and the page
data run for a spec in an epic; the files written, the grid, decisions.md, queue.md and the
epic files are committed (shared-file rules), never pushed. Prints one line naming the spec,
the milestone, its sprint and its tracker.
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
die, load = C.die, C.load


def main():
    ap = argparse.ArgumentParser(
        usage='plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>] [--cites "Q3, Q4"] '
              '[--checks "<checks>"] [--files a,b] [--depends "<milestone names>"] [--owner X] [--root PATH]'
    )
    ap.add_argument("action", choices=("add",))
    ap.add_argument("release")
    ap.add_argument("spec")
    ap.add_argument("name")
    ap.add_argument("--decision")
    ap.add_argument("--cites", default="")
    ap.add_argument("--checks", default="")
    ap.add_argument("--files", default="")
    ap.add_argument("--depends", default="")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    for label, val in (("name", a.name), ("files", a.files), ("depends", a.depends), ("checks", a.checks)):
        if "|" in val and label != "checks":
            die(f"{label} must not contain '|'")
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
    a.files = [f.strip().strip("`") for f in a.files.split(",") if f.strip()]
    own = load("lib/ownership")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    with open(C.lock_file(folder), "a") as lock:
        run(a, own, root, folder, ids, decision, lock)


def run(a, own, root, folder, ids, decision, lock):
    sp, bd = load("lib/specs"), load("lib/board")
    fcntl.flock(lock, fcntl.LOCK_EX)
    queue = folder / own.QUEUE_MD
    have = {c["num"] for c in bd.parse(own.read(queue))["cards"]} if queue.is_file() else set()
    missing = [i for i in ids if int(i[1:]) not in have]
    if missing:
        die(f"not in {queue.name}: {', '.join(missing)}")
    specs = dict(own.spec_files(folder))
    if a.spec not in specs:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    path = specs[a.spec]
    text = own.read(path)
    doc = own.read_spec(path)
    if doc["closed"]:
        die(f"spec {a.spec} is closed ({doc['closed']}): new work needs a new spec")
    epic = own.spec_epic(path)
    if decision is not None:
        sp.check_decision(folder, decision, epic)
    cites = ([f"D{decision}"] if decision is not None else []) + ids
    new = sp.new_form(text)
    if not new and not (a.files and a.checks):
        die(f"spec {a.spec} is in the old form: --files and --checks are required")
    if new and not (cites or a.checks) and doc["type"] != "iterative":
        die("--checks is required: only an iterative spec takes an empty milestone")

    comp = own.compute(folder)
    if comp["errors"]:
        own.print_errors(comp["errors"], "nothing written")
    names = {m["name"] for m in comp["milestones"]}
    if a.name in names:
        die(f"milestone '{a.name}' exists already: pick another name")
    deps = [m["name"] for m in comp["milestones"] if set(m["files"]) & set(a.files)]
    extra, unknown = own.resolve_deps(a.depends, sorted(names), {})
    if unknown:
        die(f"--depends names unknown milestones: {', '.join(unknown)}")
    deps += [d for d in extra if d not in deps]
    start = own.current_sprint(folder) if epic else None

    if new:
        tasks = []
        if cites or a.checks:
            text, tid = sp.add_task(text, list(doc["tasks"]), a.name, cites, a.checks or None)
            tasks = [tid]
        text, _ = sp.add_milestone(text, [b["id"] for b in doc["blocks"] if b["id"]], a.name, tasks,
                                   a.files, deps, start)
    else:
        text = sp.append_old_block(text, sp.old_block(a.name, a.files, deps, start, cites, a.checks))
        if text is None:
            die(f"spec {a.spec} has no '### Milestone:' block to follow")
    writes = {path: text}
    slug = path.stem.split("-", 1)[1]
    tracker = own.milestone_tracker(folder, a.spec, slug, len(doc["blocks"]), a.name)
    if doc["blocks"] and tracker.exists():
        die(f"refusing to overwrite {tracker}")
    if not tracker.exists():
        head = f"# {a.spec}: {a.name}, tracker"
        writes[tracker] = C.tracker_text(a.spec, a.name).replace(
            head, f"# {a.spec}: {a.name} ({', '.join(cites)}), tracker" if cites else head, 1)
    epic_file = own.epic_path(folder, epic) if epic else None
    if epic_file and epic_file.is_file() and decision is None:
        table, err = own.read_table(own.read(epic_file))
        if table and not err and any(r["spec"] == a.spec for r in table):
            for r in table:
                if r["spec"] == a.spec:
                    r["milestone"] = "; ".join(x for x in (r["milestone"], a.name) if x)
            writes[epic_file] = own.put_table(own.read(epic_file), table)

    old = {p: (own.read(p) if p.exists() else None) for p in writes}
    for p, t in writes.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    comp = own.compute(folder)
    if comp["errors"]:
        for p, t in old.items():
            if t is None:
                p.unlink()
            else:
                p.write_text(t, encoding="utf-8")
        own.print_errors(comp["errors"], "the milestone does not schedule; nothing written")
    if ids:
        q_text = own.read(queue)
        for i in ids:
            q_text = bd.move(q_text, int(i[1:]), "Autofix")
        bd.write(queue, q_text)
    fcntl.flock(lock, fcntl.LOCK_UN)
    if epic:
        if decision is not None:
            sp.tag_decision(folder, epic, decision)
        with contextlib.redirect_stdout(io.StringIO()):
            load("lib/grid").refresh(folder, a.release, quiet=True)
            load("sprints/swimlanes").write(folder, a.release, quiet=True)
    fcntl.flock(lock, fcntl.LOCK_EX)
    paths = [str(p) for p in writes] + [str(folder / own.SPRINTS_MD), str(folder / "decisions.md"), str(queue)]
    paths += [str(p) for p in sorted((folder / own.EPICS_DIR).glob("E*.md"))]
    C.commit(root, paths, f"docs(plan): {a.release} milestone {a.spec} {a.name}")
    fcntl.flock(lock, fcntl.LOCK_UN)
    rel = tracker.relative_to(folder).as_posix()
    if epic:
        col = own.compute(folder)["col"].get(a.name)
        print(f"milestone of spec {a.spec}: '{a.name}' in E{epic}, S{col}, tracker {rel}")
    else:
        print(f"milestone of spec {a.spec}: '{a.name}', tracker {rel}; the spec is in no epic yet, the go tags it")


if __name__ == "__main__":
    main()
