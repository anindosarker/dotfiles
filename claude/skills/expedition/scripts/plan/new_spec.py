#!/usr/bin/env python3
"""Create a spec in a release: its folder plan/specs/NN-<slug>/ with the file NN-<slug>.md and
the empty folder tasks/, and the row "| NN | [Title](plan/specs/NN-<slug>/NN-<slug>.md) |  |
scope |" (Epic cell empty) in the Deliverables table of <release>-plan.md. In a release made
before status/data/status.json it writes what it wrote then (old_spec): the flat file
plan/specs/NN-<slug>.md and the tracker of its first milestone.

Usage: python3 -I plan/new_spec.py <release> <num> <slug> "<Title>" "<scope>"
       [--owner X] [--template PATH] [--root PATH]

Template: --template PATH, else a contract stub when the project has planning rules
(plan/find_rules.py), else the bundled templates/spec.md, without its note and with the
sections 1.6 Modules, 2.1 Tasks and 2.2 Milestones empty. Write section 1, then add each piece
of work with plan/milestone.py add: it writes the module heading, the task files, the task
pointers, the milestone block and the milestone's tracker. Then run sprints/check.py.

The epic tags on go are epics/tag.py.

Refuses a superseded decision (title mark "(superseded by D<n>)", or named by a later
"- Supersedes D<n>." bullet) when the title, scope or template cites one.
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
NUM_RE = re.compile(r"^\d{2}(\.\d+)?$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
die = C.die


STUB = """---
status: not started
---
# {heading}

Follow the project planning rules: {paths}. Keep the contract in the expedition skill's SKILL.md, Stage 2, The contract.

## 1. Architecture

### 1.6 Modules

## 2. Instructions for AI

### 2.1 Tasks

### 2.2 Milestones
"""


OLD_STUB = """# {heading}

Follow the project planning rules: {paths}. Keep the contract in the expedition skill's SKILL.md, Stage 2, The contract.

## 2. Instructions for AI

### 2.1 Milestones

### Milestone: [name]

- Files owned: `[path]`, `[path]`
- Depends on: none
- Review: none
- Local CI: none
- Task 1: [step] Checks: `[command]`
- Task 2: [step] Checks: `[command]`
"""


def old_spec(a, root, own, folder, plan):
    """A release made before status/data/status.json: the flat file plan/specs/NN-<slug>.md from
    the old stub or templates/spec-flat.md, and the tracker of its first milestone."""
    spec_name = f"{a.num}-{a.slug}.md"
    specs_dir = folder / own.SPECS_DIR
    trackers_dir = folder / own.TRACKERS_DIR
    for d in (specs_dir, trackers_dir):
        d.mkdir(parents=True, exist_ok=True)
    spec = specs_dir / spec_name
    tracker = trackers_dir / f"{a.num}-{a.slug}-tracker.md"
    for p in (spec, tracker):
        if p.exists():
            die(f"refusing to overwrite {p}")
    clash = [p.name for p in specs_dir.glob(f"{a.num}-*.md")]
    if clash:
        die(f"spec {a.num} already has a file: {clash[0]}")
    row = f"| {a.num} | [{a.title}](plan/specs/{spec_name}) |  | {a.scope} |"
    new_plan = C.insert_row(plan.read_text(encoding="utf-8"), a.num, row)
    rules = [] if a.template else C.find_rules(root)
    if a.template:
        template = load_template(root, a.template, rules)
    elif rules:
        template = OLD_STUB.format(heading="[title]", paths=", ".join(rules))
    else:
        template = (C.TEMPLATES / "spec-flat.md").read_text(encoding="utf-8")
    cited = set()
    for text in (a.title, a.scope, template):
        for m in re.finditer(r"\((D\d+[^)]*)\)", text):
            cited |= {int(n) for n in re.findall(r"\bD(\d+)\b", m.group(1))}
    own.refuse_superseded(folder, cited, f"spec {spec_name}")
    spec.write_text(set_heading(template, f"# {a.num}: {a.title}"), encoding="utf-8")
    print(spec)
    tracker.write_text(C.tracker_text(a.num, a.title, True), encoding="utf-8")
    print(tracker)
    plan.write_text(new_plan, encoding="utf-8")
    print("next: fill the ### Milestone: blocks, then sprints/check.py and sprints/refresh.py "
          "(this release is format 1.0: reference/old-form/planning-guidelines.md and reference/old-form/specs.md)")
    for r in rules:
        print(f"Project planning rules: {r}")


def load_template(root, flag, rules):
    """Return template text: --template, else contract stub, else bundled."""
    if flag:
        p = Path(flag)
        if not p.is_file():
            die(f"template not found: {p}")
        return p.read_text(encoding="utf-8")
    if rules:
        return STUB.format(heading="[title]", paths=", ".join(rules))
    sp = C.load("lib/specs")
    text = "".join(l + "\n" for l in C.template("spec.md").splitlines() if not l.startswith("- Epic: E["))
    for name in ("Modules", "Tasks", "Milestones"):
        text = sp.empty_section(text, name)
    return text


def set_heading(text, heading):
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = heading + "\n"
            return "".join(lines)
    return heading + "\n\n" + text


def main():
    ap = argparse.ArgumentParser(
        usage='plan/new_spec.py <release> <num> <slug> "<Title>" "<scope>" '
              "[--owner X] [--template PATH] [--root PATH]"
    )
    ap.add_argument("release")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--owner")
    ap.add_argument("--template")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if len(a.rest) != 4:
        ap.error("expected <num> <slug> \"<Title>\" \"<scope>\"")
    a.num, a.slug, a.title, a.scope = a.rest
    if not NUM_RE.fullmatch(a.num):
        die(f"bad spec number '{a.num}', expected like 03 or 04.1")
    if not SLUG_RE.fullmatch(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    if "|" in a.title or "|" in a.scope:
        die("title and scope must not contain '|'")
    for label, val in (("title", a.title), ("scope", a.scope)):
        if "\u2014" in val:
            die(f"{label} contains an em dash")

    root = C.repo_root(a.root, a.release)
    own = C.load("lib/ownership")
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    plan = folder / f"{a.release}-plan.md"
    if not plan.is_file():
        die(f"{plan.name} missing: {plan}")
    st = C.load("lib/status")
    if not st.active(folder):
        return old_spec(a, root, own, folder, plan)

    st.load(folder)  # a store that cannot be read stops here, before anything is written
    spec_name = f"{a.num}-{a.slug}.md"
    specs_dir = folder / own.SPECS_DIR
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec = specs_dir / f"{a.num}-{a.slug}" / spec_name
    rules = [] if a.template else C.find_rules(root)
    template = load_template(root, a.template, rules)
    cited = set()
    for text in (a.title, a.scope, template):
        for m in re.finditer(r"\((D\d+[^)]*)\)", text):
            cited |= {int(n) for n in re.findall(r"\bD(\d+)\b", m.group(1))}
    own.refuse_superseded(folder, cited, f"spec {spec_name}")
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # before the plan file is read: two new specs at once
        if spec.exists():
            die(f"refusing to overwrite {spec}")
        clash = [p.name for p in specs_dir.glob(f"{a.num}-*")]
        if clash:
            die(f"spec {a.num} already has a file: {clash[0]}")
        row = f"| {a.num} | [{a.title}](plan/specs/{a.num}-{a.slug}/{spec_name}) |  | {a.scope} |"
        new_plan = C.insert_row(plan.read_text(encoding="utf-8"), a.num, row)
        (spec.parent / "tasks").mkdir(parents=True)
        spec.write_text(set_heading(template, f"# {a.num}: {a.title}"), encoding="utf-8")
        print(spec)
        plan.write_text(new_plan, encoding="utf-8")
        st.sync(folder, a.release)
        fcntl.flock(lock, fcntl.LOCK_UN)
    print("next: write section 1, then plan/milestone.py add for each piece of work, then sprints/check.py")
    for r in rules:
        print(f"Project planning rules: {r}")


if __name__ == "__main__":
    main()
