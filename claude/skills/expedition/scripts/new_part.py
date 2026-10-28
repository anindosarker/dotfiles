#!/usr/bin/env python3
"""Create a part file and its tracker in a cycle, and add the index row.

Usage: python3 -I new_part.py <cycle> <num> <slug> "<Title>" "<scope>"
       [--owner X] [--template PATH]
"""
import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

CYCLE_RE = re.compile(r"^v\d+\.\d+\.x$")
NUM_RE = re.compile(r"^\d{2}(\.\d+)?$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root():
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


def load_template(root, flag):
    """Return template text: --template, else repo override, else bundled."""
    if flag:
        p = Path(flag)
        if not p.is_file():
            die(f"template not found: {p}")
        return p.read_text(encoding="utf-8")
    override = root / ".ai" / "plans" / "part-template.md"
    if override.is_file():
        return override.read_text(encoding="utf-8")
    bundled = Path(__file__).resolve().parent.parent / "templates" / "part.md"
    if not bundled.is_file():
        die(f"bundled template missing: {bundled}")
    return bundled.read_text(encoding="utf-8")


def set_heading(text, heading):
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = heading + "\n"
            return "".join(lines)
    return heading + "\n\n" + text


def insert_row(index_text, num, row):
    lines = index_text.splitlines(keepends=True)
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## Parts")
    except StopIteration:
        die("index has no ## Parts section")
    i = start + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            die("index ## Parts section has no table")
        i += 1
    if i >= len(lines):
        die("index ## Parts section has no table")
    header = i
    if header + 1 >= len(lines) or not re.match(r"^\|[\s|:-]+\|\s*$", lines[header + 1]):
        die("index Parts table has no separator row")
    end = header + 2
    insert_at = None
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        m = ROW_RE.match(lines[end].lstrip())
        if m:
            if m.group(1) == num:
                die(f"index already has a row for part {num}")
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
        usage='new_part.py <cycle> <num> <slug> "<Title>" "<scope>" '
              "[--owner X] [--template PATH]"
    )
    ap.add_argument("cycle")
    ap.add_argument("num")
    ap.add_argument("slug")
    ap.add_argument("title")
    ap.add_argument("scope")
    ap.add_argument("--owner")
    ap.add_argument("--template")
    a = ap.parse_args()
    if not CYCLE_RE.match(a.cycle):
        die(f"bad cycle '{a.cycle}', expected like v0.7.x")
    if not NUM_RE.match(a.num):
        die(f"bad part number '{a.num}', expected like 03 or 04.1")
    if not SLUG_RE.match(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    if "|" in a.title or "|" in a.scope:
        die("title and scope must not contain '|'")
    for label, val in (("title", a.title), ("scope", a.scope)):
        if "\u2014" in val:
            die(f"{label} contains an em dash")

    root = repo_root()
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.cycle / owner
    if not folder.is_dir():
        die(f"cycle folder missing: {folder}")
    index = folder / f"{a.cycle}-plan.md"
    if not index.is_file():
        die(f"index missing: {index}")

    part_name = f"{a.num}-{a.slug}.md"
    part = folder / part_name
    tracker = folder / f"{a.num}-tracker.md"
    for p in (part, tracker):
        if p.exists():
            die(f"refusing to overwrite {p}")
    clash = [p.name for p in folder.glob(f"{a.num}-*.md") if p.name != tracker.name]
    if clash:
        die(f"part {a.num} already has a file: {clash[0]}")

    row = f"| {a.num} | [{a.title}]({part_name}) | {a.scope} |"
    new_index = insert_row(index.read_text(encoding="utf-8"), a.num, row)
    template = load_template(root, a.template)

    part.write_text(set_heading(template, f"# {a.num}: {a.title}"), encoding="utf-8")
    print(part)
    tracker.write_text(
        f"# {a.num}: {a.title}, tracker\n\n"
        f"Deviations only. Plan: [{part_name}]({part_name}).\n\n"
        "## Phase 01\n",
        encoding="utf-8",
    )
    print(tracker)
    index.write_text(new_index, encoding="utf-8")


if __name__ == "__main__":
    main()
