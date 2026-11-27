#!/usr/bin/env python3
"""Add a task to a spec: its task file and its pointer line.

Usage: python3 -I plan/task.py add <release> <spec> "<Title>" [--module 1.6.N]
       [--milestone "<name>"] [--type feat|bug] [--owner X] [--root PATH]

For a spec in the new form. Writes the file tasks/NN-<slug>.md from templates/task.md ("status:
not started", --type, default feat; NN is the next task number of the spec) and the line
"- NN <Title> · module 1.6.N · tasks/NN-<slug>.md" at the end of 2.1 Tasks. --module names the
task's module: default the module of the milestone's first task, else the spec's last module.
--milestone adds the number to that milestone's "- Tasks:" line; a task joins a milestone only
while the milestone is not started. Without --milestone the task is in no milestone yet. A new
piece of work with its own module and milestone is plan/milestone.py add; a task's status is
status/status.py.

Refuses, writing nothing: a spec with no file, in the old form, or done; an unknown module or
milestone; a milestone that has started. Commits the spec, the task file and status.json.
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
die, load = C.die, C.load


def main():
    ap = argparse.ArgumentParser(
        usage='plan/task.py add <release> <spec> "<Title>" [--module 1.6.N] [--milestone "<name>"] '
              "[--type feat|bug] [--owner X] [--root PATH]")
    ap.add_argument("action", choices=("add",))
    ap.add_argument("release")
    ap.add_argument("spec")
    ap.add_argument("title")
    ap.add_argument("--module")
    ap.add_argument("--milestone")
    ap.add_argument("--type", choices=("feat", "bug"), default="feat")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    if "\u2014" in a.title or "|" in a.title:
        die("the title contains an em dash or '|'")
    own, sp, st = load("lib/ownership"), load("lib/specs"), load("lib/status")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    path = dict(own.spec_files(folder)).get(a.spec)
    if path is None:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    text = own.read(path)
    if not sp.new_form(text) or path.parent.name != path.stem:
        die(f"spec {a.spec} is in the old form: write its Task line by hand")
    doc = own.read_spec(path)
    stored = st.active(folder)
    data = st.build(folder, a.release) if stored else None
    if stored and st.find(data, a.spec)[1]["status"] == "done":
        die(f"spec {a.spec} is done and takes nothing: the work is a new spec")
    block = None
    if a.milestone:
        block = next((b for b in doc["blocks"] if b["name"] == a.milestone), None)
        if block is None:
            die(f"spec {a.spec} has no milestone '{a.milestone}'")
        if stored:
            state = next((m["status"] for m in data["milestones"]
                          if m["spec"] == a.spec and m["name"] == a.milestone), "not started")
        else:
            state = "not started" if sp.grid_cells(folder, a.spec).get(a.milestone, "·") == "·" else "started"
        if state != "not started":
            die(f"milestone '{a.milestone}' is {state}: a task joins a milestone only while it is "
                "not started; add the work as its own milestone (plan/milestone.py add)")
    module = a.module or (block["tasks"][0]["module"] if block and block["tasks"] else None) \
        or (list(doc["modules"])[-1] if doc["modules"] else None)
    if module not in doc["modules"]:
        die(f"spec {a.spec} has no module {module}: name one with --module")
    number = sp.next_task(doc, path)
    rel = f"tasks/{number}-{C.slugify(a.title)}.md"
    text = sp.add_pointer(text, number, a.title, module, rel)
    if block:
        text = sp.link_task(text, a.milestone, number)
    out = path.parent / rel
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sp.task_file_text(a.title, a.type), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        if stored:
            with contextlib.redirect_stdout(io.StringIO()):
                st.sync(folder, a.release)
        C.commit(root, [path, out] + st.changed(), f"docs(plan): {a.release} task {a.spec} {number} {a.title}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    where = f"in milestone '{a.milestone}'" if block else "in no milestone yet"
    print(f"task {number} of spec {a.spec}: '{a.title}' {where}, module {module}, file {out.relative_to(folder).as_posix()}")


if __name__ == "__main__":
    main()
