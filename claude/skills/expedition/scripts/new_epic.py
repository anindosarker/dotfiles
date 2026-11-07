#!/usr/bin/env python3
"""Create an epic file (epics/NN-<slug>.md) and the tracker of its first milestone
(trackers/NN-<slug>-tracker.md) in a release, and add the row
"| NN | [Title](epics/NN-<slug>.md) | scope |" to the Epics table of plan.md.

Usage: python3 -I new_epic.py <release> <num> <slug> "<Title>" "<scope>"
       [--owner X] [--template PATH] [--root PATH]

Template: --template PATH, else a contract stub when the project has planning
rules (find_rules.py), else the bundled templates/epic.md. Section 2.1 holds one "### Milestone: [name]" block with
the lines Files owned, Depends on, Review and its Task lines; write one block per
milestone, then run ownership.py and sprints.py. A later milestone's tracker is
trackers/NN-<milestone-slug>-tracker.md.
"""
import argparse
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
NUM_RE = re.compile(r"^\d{2}(\.\d+)?$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root(flag=None):
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        die("not inside a git repository")
    return Path(out.stdout.strip())


def detect_owner(root, flag):
    if flag:
        return flag
    plans = root / ".ai" / "plans"
    counts = collections.Counter(
        p.name for p in plans.glob("v*.x/*") if p.is_dir()
    )
    if not counts:
        die("no owner found under .ai/plans/v*.x/*/; pass --owner")
    return counts.most_common(1)[0][0]


def num_key(num):
    return tuple(int(x) for x in num.split("."))


STUB = """# {heading}

Follow the project planning rules: {paths}. Keep the expedition contract.

## 2. Instructions for AI

### 2.1 Milestones

### Milestone: [name]

- Files owned: `[path]`, `[path]`
- Depends on: none
- Review: none
- Task 1: [step] Checks: `[command]`
- Task 2: [step] Checks: `[command]`
"""


def find_rules(root):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "find_rules.py"
    spec = importlib.util.spec_from_file_location("find_rules", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_rules(root)


def load_template(root, flag, rules):
    """Return template text: --template, else contract stub, else bundled."""
    if flag:
        p = Path(flag)
        if not p.is_file():
            die(f"template not found: {p}")
        return p.read_text(encoding="utf-8")
    if rules:
        return STUB.format(heading="[title]", paths=", ".join(rules))
    tdir = Path(__file__).resolve().parent.parent / "templates"
    bundled = tdir / "epic.md"
    if not bundled.is_file():
        die(f"bundled template missing: {bundled}")
    return bundled.read_text(encoding="utf-8")


def tracker_text(num, title):
    """templates/tracker.md with the header filled in and Status: planned.

    The optional Attention and Notes sections are left out; empty is normal.
    """
    path = Path(__file__).resolve().parent.parent / "templates" / "tracker.md"
    if not path.is_file():
        die(f"bundled template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# "):
            line = f"# {num}: {title}, tracker"
        elif line.startswith("Status:"):
            line = "Status: planned"
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def set_heading(text, heading):
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = heading + "\n"
            return "".join(lines)
    return heading + "\n\n" + text


def insert_row(plan_text, num, row):
    lines = plan_text.splitlines(keepends=True)
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## Epics")
    except StopIteration:
        die("plan.md has no ## Epics section")
    i = start + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            die("plan.md ## Epics section has no table")
        i += 1
    if i >= len(lines):
        die("plan.md ## Epics section has no table")
    header = i
    if header + 1 >= len(lines) or not re.match(r"^\|[\s|:-]+\|\s*$", lines[header + 1]):
        die("plan.md Epics table has no separator row")
    end = header + 2
    insert_at = None
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        m = ROW_RE.match(lines[end].lstrip())
        if m:
            if m.group(1) == num:
                die(f"plan.md already has a row for epic {num}")
            if insert_at is None and num_key(m.group(1)) > num_key(num):
                insert_at = end
        end += 1
    if insert_at is None:
        insert_at = end
    if insert_at > 0 and not lines[insert_at - 1].endswith("\n"):
        lines[insert_at - 1] += "\n"
    lines.insert(insert_at, row + "\n")
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(
        usage='new_epic.py <release> <num> <slug> "<Title>" "<scope>" '
              "[--owner X] [--template PATH] [--root PATH]"
    )
    ap.add_argument("release")
    ap.add_argument("num")
    ap.add_argument("slug")
    ap.add_argument("title")
    ap.add_argument("scope")
    ap.add_argument("--owner")
    ap.add_argument("--template")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.match(a.num):
        die(f"bad epic number '{a.num}', expected like 03 or 04.1")
    if not SLUG_RE.match(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    if "|" in a.title or "|" in a.scope:
        die("title and scope must not contain '|'")
    for label, val in (("title", a.title), ("scope", a.scope)):
        if "\u2014" in val:
            die(f"{label} contains an em dash")

    root = repo_root(a.root)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    plan = folder / "plan.md"
    if not plan.is_file():
        legacy = folder / f"{a.release}-plan.md"
        if legacy.is_file():
            die(f"legacy layout ({legacy.name}, specs/): new_epic.py writes plan.md and epics/ only")
        die(f"plan.md missing: {plan}")

    epic_name = f"{a.num}-{a.slug}.md"
    epics_dir = folder / "epics"
    trackers_dir = folder / "trackers"
    for d in (epics_dir, trackers_dir):
        d.mkdir(exist_ok=True)
    epic = epics_dir / epic_name
    tracker = trackers_dir / f"{a.num}-{a.slug}-tracker.md"
    for p in (epic, tracker):
        if p.exists():
            die(f"refusing to overwrite {p}")
    clash = [p.name for p in epics_dir.glob(f"{a.num}-*.md")]
    if clash:
        die(f"epic {a.num} already has a file: {clash[0]}")

    row = f"| {a.num} | [{a.title}](epics/{epic_name}) | {a.scope} |"
    new_plan = insert_row(plan.read_text(encoding="utf-8"), a.num, row)
    rules = [] if a.template else find_rules(root)
    template = load_template(root, a.template, rules)

    epic.write_text(set_heading(template, f"# {a.num}: {a.title}"), encoding="utf-8")
    print(epic)
    tracker.write_text(tracker_text(a.num, a.title), encoding="utf-8")
    print(tracker)
    plan.write_text(new_plan, encoding="utf-8")
    print("next: fill the ### Milestone: blocks, then ownership.py and sprints.py")
    for r in rules:
        print(f"Project planning rules: {r}")


if __name__ == "__main__":
    main()
