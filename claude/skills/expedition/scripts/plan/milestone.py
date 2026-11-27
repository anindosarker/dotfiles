#!/usr/bin/env python3
"""Add a piece of work to a spec: the next module, its task files and its milestone. A fix found
during a run, follow-up work, a feedback item on a spec in progress, and each milestone of a new
spec go this way.

Usage: python3 -I plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>]
       [--task "<Task title>"]... [--type feat|bug] [--module 1.6.N] [--cites "Q3, Q4"]
       [--files a,b] [--depends "<milestone names>"] [--checks "<checks>"] [--epic E<n>]
       [--owner X] [--root PATH]

A spec in the new form (sections 1.6 Modules, 2.1 Tasks, 2.2 Milestones) gets three additions,
and the numbers only go up:
- the module "#### 1.6.N <Name> (<ids>)" with one line to fill; the cite is --decision, then
  the --cites cards. --module names an existing module instead, and no module is written;
- one task per --task (with none, one task named like the milestone): the file
  tasks/NN-<slug>.md from templates/task.md, "status: not started", --type (default feat), and
  its pointer line in 2.1 Tasks;
- the milestone "#### 2.2.N Milestone: <Name>" with "- Tasks:", "- Files owned:" when --files,
  "- Depends on:" when a dependency exists (every other milestone owning one of the --files,
  plus --depends). With neither, it is built at the same time as the others.
A spec in the old form ("### Milestone:" blocks with "- Task N:" lines) gets one block with one
task line; --files and --checks are required there.
While the spec is in an epic: the block gets "- Starts: S<n>", the current sprint, and the name
joins the Milestone cell of the spec's rows in the epic file. --decision also adds the decision
to that epic (its decisions line, an Ownership row, the "#E<n>" tag, the card to In progress).
A spec in no epic yet gets the additions only; the go tags it.
The tracker is run/trackers/NN-<name slug>-tracker.md.

A spec that is done takes nothing (status.json; in an earlier release: every grid row "[x]").
With --decision that is refused: the work is a new spec. Without, a fix becomes a follow-up
spec NN.M with that one milestone, in the epic of <spec> while it has an unfinished row, else
in the one running epic (--epic when several run).

Refuses, writing nothing: a D id among --cites; a Q id not in queue.md; a decision not in
decisions.md, superseded, or in another epic; a spec with no file; a done spec with --decision;
an unknown --module; a milestone name already taken; milestones that no longer schedule. Then
each cited card moves to Autofix; the refresh chain (lib/grid.py refresh, which also writes
status.json) and the page data run; everything written is committed, never pushed. Prints one
line naming the spec, the milestone, its sprint and its tracker.
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
EPIC_RE = re.compile(r"^E(\d+)$")
UNFINISHED = ("[ ]", "[~]", "·")
die, load = C.die, C.load

FOLLOW_UP = """---
status: not started
---
# {num}: {title}
- Epic: E{epic}

## 1. Architecture

### 1.1 Overview

Follow-up of spec {spec}{cites}.

### 1.2 Goals

- Acceptance: the Verification list of each task holds.

### 1.6 Modules

## 2. Instructions for AI

### 2.1 Tasks

### 2.2 Milestones
"""


def main():
    ap = argparse.ArgumentParser(
        usage='plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>] [--task "<title>"]... '
              '[--type feat|bug] [--module 1.6.N] [--cites "Q3, Q4"] [--files a,b] '
              '[--depends "<milestone names>"] [--checks "<checks>"] [--epic E<n>] [--owner X] [--root PATH]'
    )
    ap.add_argument("action", choices=("add",))
    ap.add_argument("release")
    ap.add_argument("spec")
    ap.add_argument("name")
    ap.add_argument("--decision")
    ap.add_argument("--task", action="append", default=[])
    ap.add_argument("--type", choices=("feat", "bug"), default="feat")
    ap.add_argument("--module")
    ap.add_argument("--cites", default="")
    ap.add_argument("--checks", default="")
    ap.add_argument("--files", default="")
    ap.add_argument("--depends", default="")
    ap.add_argument("--epic")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    for label, val in [("name", a.name), ("files", a.files), ("depends", a.depends), ("checks", a.checks)] \
            + [("task", x) for x in a.task]:
        if "|" in val and label != "checks":
            die(f"{label} must not contain '|'")
        if "\u2014" in val:
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
    want_epic = None
    if a.epic:
        m = EPIC_RE.match(a.epic)
        if not m:
            die(f"bad epic '{a.epic}', expected like E12")
        want_epic = int(m.group(1))
    a.files = [f.strip().strip("`") for f in a.files.split(",") if f.strip()]
    own = load("lib/ownership")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    with open(C.lock_file(folder), "a") as lock:
        run(a, own, root, folder, ids, decision, want_epic, lock)


def spec_done(own, st, folder, num, rows):
    """True when the spec is finished: its status in status.json, or every grid row "[x]"."""
    if st.active(folder):
        return st.find(st.build(folder, folder.parent.name), num)[1]["status"] == "done"
    cells = [c for _, cs in rows.get(num, []) for c in cs if c]
    return bool(cells) and all(c == "[x]" for c in cells)


def grid_by_spec(own, folder):
    """{spec number: [(epic, cells)]} of status/sprints.md."""
    out = {}
    for label, cells in own.grid(folder)[1]:
        m = re.match(r"^E(\d+)\s+(\d{2}(?:\.\d+)?)\s", label)
        if m:
            out.setdefault(m.group(2), []).append((int(m.group(1)), cells))
    return out


def run(a, own, root, folder, ids, decision, want_epic, lock):
    sp, bd, st = load("lib/specs"), load("lib/board"), load("lib/status")
    fcntl.flock(lock, fcntl.LOCK_EX)
    queue = folder / own.QUEUE_MD
    have = {c["num"] for c in bd.parse(own.read(queue))["cards"]} if queue.is_file() else set()
    missing = [i for i in ids if int(i[1:]) not in have]
    if missing:
        die(f"not in {queue.name}: {', '.join(missing)}")
    specs = dict(own.spec_files(folder))
    if a.spec not in specs:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    path, num = specs[a.spec], a.spec
    text = own.read(path)
    epic = own.spec_epic(path)
    if decision is not None:
        sp.check_decision(folder, decision, epic)
    rows = grid_by_spec(own, folder)
    new = sp.new_form(text)
    if not new and not (a.files and a.checks):
        die(f"spec {a.spec} is in the old form: --files and --checks are required")
    cites = ([f"D{decision}"] if decision is not None else []) + ids
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

    writes = {}
    follow = spec_done(own, st, folder, a.spec, rows)
    if follow:
        if decision is not None:
            die(f"spec {a.spec} is done and takes nothing: D{decision} is work for a new spec")
        if not epic:
            die(f"spec {a.spec} is in no epic")
        running = sorted({e for lst in rows.values() for e, cells in lst if any(c in UNFINISHED for c in cells)})
        if not running:
            die("no epic is running: file a queue card instead (queue/item.py <release> Q \"<title>\")")
        if want_epic:
            if want_epic not in running:
                die(f"E{want_epic} is not running; running: {', '.join(f'E{e}' for e in running)}")
            epic = want_epic
        elif epic not in running:
            if len(running) > 1:
                die(f"several epics run ({', '.join(f'E{e}' for e in running)}): pass --epic E<n>")
            epic = running[0]
        plan = folder / f"{a.release}-plan.md"
        plan_text = own.read(plan)
        taken = set(specs) | set(re.findall(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|", plan_text, re.M))
        base = a.spec.split(".")[0]
        last = max((int(n.split(".")[1]) for n in taken if re.fullmatch(re.escape(base) + r"\.\d+", n)), default=0)
        num = f"{base}.{last + 1}"
        slug = C.slugify(a.name)
        tail = f" ({', '.join(ids)})" if ids else ""
        if new:
            path = folder / own.SPECS_DIR / f"{num}-{slug}" / f"{num}-{slug}.md"
            text = FOLLOW_UP.format(num=num, title=a.name, epic=epic, spec=a.spec, cites=tail)
            link = f"plan/specs/{num}-{slug}/{num}-{slug}.md"
        else:
            path = folder / own.SPECS_DIR / f"{num}-{slug}.md"
            text = (f"# {num}: {a.name}\n- Epic: E{epic}\n\nFollow-up of spec {a.spec}{tail}.\n\n"
                    "- Acceptance: the checks of Task 1 pass.\n\n"
                    "## 2. Instructions for AI\n\n### 2.1 Milestones\n\n### Milestone: [name]\n")
            link = f"plan/specs/{path.name}"
        writes[plan] = C.insert_row(plan_text, num, f"| {num} | [{a.name}]({link}) | E{epic} | {a.name} |")
    start = own.current_sprint(folder) if epic else None

    doc = own.read_spec(path) if path.is_file() else {"blocks": [], "tasks": {}, "modules": {}}
    if new:
        module = a.module
        if module and module not in doc["modules"]:
            die(f"spec {a.spec} has no module {module}")
        if not module:
            text, module = sp.add_module(text, list(doc["modules"]), a.name, cites)
        number, tasks = int(sp.next_task(doc, path)), []
        for title in a.task or [a.name]:
            n = f"{number + len(tasks):02d}"
            rel = f"tasks/{n}-{C.slugify(title)}.md"
            text = sp.add_pointer(text, n, title, module, rel)
            writes[path.parent / rel] = sp.task_file_text(title, a.type)
            tasks.append(n)
        text, _ = sp.add_milestone(text, [b["id"] for b in doc["blocks"] if b["id"]], a.name, tasks,
                                   a.files, deps, start)
    else:
        block = sp.old_block(a.name, a.files, deps, start, cites, a.checks)
        text = text.replace("### Milestone: [name]\n", block) if follow else sp.append_old_block(text, block)
        if text is None:
            die(f"spec {a.spec} has no '### Milestone:' block to follow")
    writes[path] = text
    stem = path.stem.split("-", 1)[1]
    tracker = (folder / own.TRACKERS_DIR / f"{num}-{stem}-tracker.md" if follow and not new
               else own.milestone_tracker(folder, num, stem, len(doc["blocks"]), a.name))
    if tracker.exists() and (doc["blocks"] or follow):
        die(f"refusing to overwrite {tracker}")
    if not tracker.exists():
        head = f"# {num}: {a.name}, tracker"
        writes[tracker] = C.tracker_text(num, a.name, not st.active(folder)).replace(
            head, f"# {num}: {a.name} ({', '.join(cites)}), tracker" if cites else head, 1)
    epic_file = own.epic_path(folder, epic) if epic else None
    if epic_file and epic_file.is_file() and decision is None:
        et = own.read(epic_file)
        table, err = own.read_table(et)
        if follow:
            sm = own.SPECS_LINE_RE.search(et)
            have_specs = [s.strip() for s in (sm.group(1) if sm else "").split(",") if s.strip()]
            et = own.set_field(et, "Specs", ", ".join(sorted(have_specs + [num], key=own.num_key)))
            if table is not None and not err:
                table.append({"decision": None, "title": "", "files": a.files, "spec": num,
                              "milestone": a.name, "sprint": ""})
                writes[epic_file] = own.put_table(et, table)
            else:
                writes[epic_file] = et
        elif table and not err and any(r["spec"] == num for r in table):
            for r in table:
                if r["spec"] == num:
                    r["milestone"] = "; ".join(x for x in (r["milestone"], a.name) if x)
            writes[epic_file] = own.put_table(et, table)

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
    if epic and decision is not None:
        sp.tag_decision(folder, epic, decision)
    with contextlib.redirect_stdout(io.StringIO()):
        if epic:
            load("lib/grid").refresh(folder, a.release, quiet=True)
            load("sprints/swimlanes").write(folder, a.release, quiet=True)
        elif st.active(folder):
            st.sync(folder, a.release)
    fcntl.flock(lock, fcntl.LOCK_EX)
    paths = [str(p) for p in list(writes) + st.changed()]
    paths += [str(folder / own.SPRINTS_MD), str(folder / "decisions.md"), str(queue)]
    paths += [str(p) for p in sorted((folder / own.EPICS_DIR).glob("E*.md"))]
    C.commit(root, paths, f"docs(plan): {a.release} milestone {num} {a.name}")
    fcntl.flock(lock, fcntl.LOCK_UN)
    rel = tracker.relative_to(folder).as_posix()
    what = f"follow-up spec {num} of spec {a.spec}: milestone" if follow else f"milestone of spec {num}:"
    if epic:
        col = own.compute(folder)["col"].get(a.name)
        print(f"{what} '{a.name}' in E{epic}, S{col}, tracker {rel}")
    else:
        print(f"{what} '{a.name}', tracker {rel}; the spec is in no epic yet, the go tags it")


if __name__ == "__main__":
    main()
