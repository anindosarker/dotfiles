#!/usr/bin/env python3
"""Create a spec file (plan/specs/NN-<slug>.md) and the tracker of its first milestone
(run/trackers/NN-<slug>-tracker.md) in a release, and add the row
"| NN | [Title](plan/specs/NN-<slug>.md) |  | scope |" (Epic cell empty) to the Deliverables table of
<release>-plan.md.

Usage: python3 -I new_spec.py <release> <num> <slug> "<Title>" "<scope>"
       [--owner X] [--template PATH] [--root PATH]

Template: --template PATH, else a contract stub when the project has planning
rules (find_rules.py), else the bundled templates/spec.md. Section 2.1 holds one "### Milestone: [name]" block with
the lines Files owned, Depends on, Review and its Task lines; write one block per
milestone, then run ownership.py and sprints.py. A later milestone's tracker is
run/trackers/NN-<milestone-slug>-tracker.md.

Epic tag mode, on go: python3 -I new_spec.py <release> --epic E<n> <spec numbers or D ids>
[--owner X] [--root PATH]. A D id resolves to the specs citing it. Each named spec gets the line
"- Epic: E<n>" directly under its title line; each decision those specs cite (and each named
D id) gets the tag line "[E<n>]" directly under its heading in decisions.md, and the spec's
Deliverables row gets E<n> in its Epic cell, and plan/epics/E<n>.md gets "Starts: S<n>" under
its Specs: line: the current sprint of status/sprints.md as it is at that moment, before the
epic's rows exist (the first column holding a "[ ]" or "·" cell, else the column after the
last; S1 for an empty grid). An existing Epic line, epic tag or Starts value is kept and
reported; a missing epic file is refused. Each file is read right before its write.

Both modes refuse a superseded decision (heading "(superseded by D<n>)", or named by a later
"- Supersedes D<n>." bullet): create mode when the title, scope or template cites one, tag mode
when a named spec cites one or a named D id is one.
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
EPIC_RE = re.compile(r"^E\d+$")


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
    bundled = tdir / "spec.md"
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
        start = next(i for i, l in enumerate(lines) if l.strip() == "## Deliverables")
    except StopIteration:
        die("plan has no ## Deliverables section")
    i = start + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            die("plan ## Deliverables section has no table")
        i += 1
    if i >= len(lines):
        die("plan ## Deliverables section has no table")
    header = i
    if header + 1 >= len(lines) or not re.match(r"^\|[\s|:-]+\|\s*$", lines[header + 1]):
        die("plan Deliverables table has no separator row")
    end = header + 2
    insert_at = None
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        m = ROW_RE.match(lines[end].lstrip())
        if m:
            if m.group(1) == num:
                die(f"plan already has a row for spec {num}")
            if insert_at is None and num_key(m.group(1)) > num_key(num):
                insert_at = end
        end += 1
    if insert_at is None:
        insert_at = end
    if insert_at > 0 and not lines[insert_at - 1].endswith("\n"):
        lines[insert_at - 1] += "\n"
    lines.insert(insert_at, row + "\n")
    return "".join(lines)


def load_ownership():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "ownership.py"
    spec = importlib.util.spec_from_file_location("ownership", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refuse_superseded(folder, nums, what):
    """Die when any of the D numbers is superseded."""
    heads, bullets = load_ownership().supersedes(folder)
    gone = {**bullets, **heads}
    hit = sorted(n for n in nums if n in gone)
    if hit:
        die(f"{what} cites superseded " + ", ".join(f"D{n} (by D{gone[n]})" for n in hit)
            + ": cite the current decision")


def tag_epic(folder, epic, items):
    """Write "- Epic: E<n>" into each named spec (a D id names the specs citing it),
    "[E<n>]" under each decision those specs cite and each named D id, and the epic's
    "Starts: S<n>" line."""
    own = load_ownership()
    epic_file = folder / own.EPICS_DIR / f"{epic}.md"
    if not epic_file.is_file():
        die(f"{epic_file} missing: run new_epic_file.py first")
    files = dict(own.spec_files(folder))
    nums, specs = set(), set()
    for item in items:
        d = re.match(r"^D(\d+)$", item)
        if d:
            nums.add(int(d.group(1)))
            hit = [num for num, p in files.items() if int(d.group(1)) in own.spec_cites(p)]
            if not hit:
                print(f"{item}: no spec cites it")
            specs.update(hit)
        elif item in files:
            specs.add(item)
        else:
            die(f"'{item}' is neither a spec number with a file nor a D id")
    refuse_superseded(folder, nums, "named D id")
    for num in sorted(specs, key=own.num_key):
        refuse_superseded(folder, own.spec_cites(files[num]), f"spec {files[num].name}")
        nums |= own.spec_cites(files[num])
    path = folder / "decisions.md"
    if not path.is_file():
        die(f"decisions.md missing: {path}")
    tags = own.read_tags(folder)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    missing = sorted(nums - set(tags))
    if missing:
        die(f"not in decisions.md: {', '.join(f'D{n}' for n in missing)}")
    marked, kept_specs = [], []
    for num in sorted(specs, key=own.num_key):
        old = own.spec_epic(files[num])
        if old:
            kept_specs.append(f"{num} E{old}")
            continue
        elines = files[num].read_text(encoding="utf-8").splitlines(keepends=True)
        title = next((i for i, l in enumerate(elines) if l.startswith("# ")), None)
        if title is None:
            die(f"{files[num].name} has no title line")
        elines.insert(title + 1, f"- Epic: {epic}\n")
        files[num].write_text("".join(elines), encoding="utf-8")
        marked.append(num)
    print(f"{epic} specs: {', '.join(marked) or 'none'}")
    start = f"S{own.current_sprint(folder)}"
    kept_start = own.set_starts(epic_file, start)
    print(f"{epic} Starts: {kept_start} kept" if kept_start else f"{epic} Starts: {start}")
    plan = folder / f"{folder.parent.name}-plan.md"
    if plan.is_file():
        plines = plan.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, l in enumerate(plines):
            r = ROW_RE.match(l.lstrip())
            cells = l.rstrip("\n").split("|")
            if r and r.group(1) in specs and len(cells) >= 6 and not cells[3].strip():
                cells[3] = f" {epic} "
                plines[i] = "|".join(cells) + "\n"
        plan.write_text("".join(plines), encoding="utf-8")
    else:
        print(f"warning: {plan.name} missing, Epic cells not written")
    if kept_specs:
        print(f"kept specs: {', '.join(kept_specs)}")
    tagged, kept = [], []
    for n in sorted(nums, key=lambda n: -tags[n]["line"]):
        t = tags[n]
        if t["epic"]:
            kept.append(f"D{n} E{t['epic']}" + (" done" if t["done"] else ""))
            continue
        lines.insert(t["line"] + 1, f"[{epic}]\n")
        tagged.append(n)
    path.write_text("".join(lines), encoding="utf-8")
    print(f"{epic}: {', '.join(f'D{n}' for n in sorted(tagged)) or 'nothing tagged'}")
    if kept:
        print(f"kept: {', '.join(sorted(kept, key=lambda k: int(k.split()[0][1:])))}")


def main():
    ap = argparse.ArgumentParser(
        usage='new_spec.py <release> <num> <slug> "<Title>" "<scope>" '
              "[--owner X] [--template PATH] [--root PATH]\n"
              "       new_spec.py <release> --epic E<n> <spec numbers or D ids> [--owner X] [--root PATH]"
    )
    ap.add_argument("release")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--epic", help="tag mode: write - Epic: E<n> into each spec and [E<n>] under each cited decision")
    ap.add_argument("--owner")
    ap.add_argument("--template")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if a.epic:
        if not EPIC_RE.match(a.epic):
            die(f"bad epic '{a.epic}', expected like E3")
        items = [s.strip() for x in a.rest for s in x.split(",") if s.strip()]
        if not items:
            die("--epic needs spec numbers or D ids")
        root = repo_root(a.root)
        folder = load_ownership().release_folder(root, detect_owner(root, a.owner), a.release)
        tag_epic(folder, a.epic, items)
        return
    if len(a.rest) != 4:
        ap.error("expected <num> <slug> \"<Title>\" \"<scope>\"")
    a.num, a.slug, a.title, a.scope = a.rest
    if not NUM_RE.match(a.num):
        die(f"bad spec number '{a.num}', expected like 03 or 04.1")
    if not SLUG_RE.match(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    if "|" in a.title or "|" in a.scope:
        die("title and scope must not contain '|'")
    for label, val in (("title", a.title), ("scope", a.scope)):
        if "\u2014" in val:
            die(f"{label} contains an em dash")

    root = repo_root(a.root)
    own = load_ownership()
    folder = own.release_folder(root, detect_owner(root, a.owner), a.release)
    plan = folder / f"{a.release}-plan.md"
    if not plan.is_file():
        die(f"{plan.name} missing: {plan}")

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
    new_plan = insert_row(plan.read_text(encoding="utf-8"), a.num, row)
    rules = [] if a.template else find_rules(root)
    template = load_template(root, a.template, rules)
    cited = set()
    for text in (a.title, a.scope, template):
        for m in re.finditer(r"\((D\d+[^)]*)\)", text):
            cited |= {int(n) for n in re.findall(r"\bD(\d+)\b", m.group(1))}
    refuse_superseded(folder, cited, f"spec {spec_name}")

    spec.write_text(set_heading(template, f"# {a.num}: {a.title}"), encoding="utf-8")
    print(spec)
    tracker.write_text(tracker_text(a.num, a.title), encoding="utf-8")
    print(tracker)
    plan.write_text(new_plan, encoding="utf-8")
    print("next: fill the ### Milestone: blocks, then ownership.py and sprints.py")
    for r in rules:
        print(f"Project planning rules: {r}")


if __name__ == "__main__":
    main()
